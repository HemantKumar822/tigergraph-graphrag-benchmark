'use client';

import React, { useState, useRef } from 'react';
import { getApiUrl } from '../../utils/apiUrl';

export default function UploadForm() {
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [statusMsg, setStatusMsg] = useState('');
  const [logs, setLogs] = useState<{msg: string, type: 'status' | 'warning' | 'error' | 'complete'}[]>([]);
  const [progress, setProgress] = useState(0);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [dbStats, setDbStats] = useState<{tokens?: number, vectors: number, documents: number, entities: number} | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Backend Gateway Health Polling Subsystem
  React.useEffect(() => {
    let active = true;
    const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
    
    const auditGatewayHealth = async () => {
      try {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), 2500); // Time out quickly
        
        const res = await fetch(`http://${host}:8080/api/health`, { 
          signal: controller.signal,
          cache: 'no-store'
        });
        clearTimeout(id);
        
        if (active) {
            setBackendOnline(res.ok);
            if (res.ok) {
                try {
                    const statsRes = await fetch(`http://${host}:8080/api/ingestion/stats`, { cache: 'no-store' });
                    const statsData = await statsRes.json();
                    if (statsData?.status === 'success') {
                        setDbStats(statsData.data);
                    }
                } catch (e) { console.error(e) }
            }
        }
      } catch {
        if (active) {
            setBackendOnline(false);
            setDbStats(null);
        }
      }
    };

    auditGatewayHealth();
    const heartbeat = setInterval(auditGatewayHealth, 5000);
    return () => {
      active = false;
      clearInterval(heartbeat);
    };
  }, []);

  // Autoscroll logs to bottom
  React.useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setIsProcessing(true);
    setLogs([]);
    setProgress(0);
    setUploadStatus('idle');
    setStatusMsg(`Processing ${files.length} file(s)...`);

    const uploadedFiles: string[] = [];

    // Phase 1: Upload all files
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);

      try {
        setStatusMsg(`Uploading ${file.name} (${i + 1}/${files.length})...`);
        const response = await fetch(getApiUrl('/api/ingestion/upload'), {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();

        if (!response.ok || result.status === 'error') {
          const errMsg = result?.error?.message || `Upload failed for ${file.name}`;
          setLogs(prev => [...prev, { msg: errMsg, type: 'error' }]);
          continue;
        }

        uploadedFiles.push(result.data.filename);
        setLogs(prev => [...prev, { msg: `Uploaded: ${result.data.filename}`, type: 'status' }]);
      } catch (err: unknown) {
        const rawMsg = err instanceof Error ? err.message : 'Unknown upload error';
        setLogs(prev => [...prev, { msg: `Upload failed: ${rawMsg}`, type: 'error' }]);
      }
    }

    setIsUploading(false);
    setStatusMsg(`Uploaded ${uploadedFiles.length}/${files.length}. Starting ingestion...`);

    // Phase 2: Ingest uploaded files sequentially
    for (const filename of uploadedFiles) {
      await ingestFile(filename);
    }

    setStatusMsg(`Ingestion complete for ${uploadedFiles.length} file(s).`);
    setIsProcessing(false);
    setUploadStatus(uploadedFiles.length > 0 ? 'success' : 'error');

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const ingestFile = async (filename: string) => {
    setStatusMsg(`Ingesting ${filename}...`);
    try {
      const origin = window.location.hostname;
      const streamResponse = await fetch(`http://${origin}:8080/api/ingestion/process?filename=${encodeURIComponent(filename)}`);
      if (!streamResponse.body) throw new Error('Remote telemetry stream severed by server.');

      const reader = streamResponse.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              setLogs(prev => [...prev, { msg: `${filename}: ${data.msg}`, type: data.event }]);
              if (data.progress !== undefined) setProgress(data.progress);
              if (data.event === 'complete') {
                setLogs(prev => [...prev, { msg: `${filename}: ✓ Complete`, type: 'complete' }]);
                return { status: 'success', summary: data.summary };
              }
            } catch (e) {
              setLogs(prev => [...prev, { msg: `Parse error for ${filename}`, type: 'warning' }]);
            }
          }
        }
      }
      throw new Error('Stream ended unexpectedly');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown ingestion error';
      setLogs(prev => [...prev, { msg: `Ingest error ${filename}: ${msg}`, type: 'error' }]);
      return { status: 'error', error: msg };
    }
  };

  const handleClearData = async () => {
    if (!window.confirm("Are you sure you want to completely clear ALL internal Vector and Graph data? This cannot be undone.")) {
      return;
    }

    setIsClearing(true);
    setLogs([]);
    setProgress(0);
    setUploadStatus('idle');
    setStatusMsg('Clearing all internal databases...');

    try {
      const response = await fetch(getApiUrl('/api/ingestion/clear'), {
        method: 'POST'
      });

      const result = await response.json();

      if (!response.ok || result.status === 'error') {
        throw new Error(result.error?.message || 'System clearance failed');
      }

      setUploadStatus('success');
      setStatusMsg('Databases cleared successfully! 🗑️');
      
      setTimeout(() => {
        if (uploadStatus === 'success') {
          setUploadStatus('idle');
          setStatusMsg('');
        }
      }, 4000);

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to wipe datasets.';
      setUploadStatus('error');
      setStatusMsg(message);
    } finally {
      setIsClearing(false);
    }
  };

  const isBusy = isUploading || isProcessing || isClearing;

  return (
    <div className="w-full max-w-7xl mx-auto px-4 md:px-6 lg:px-8 mb-4 space-y-3">
      {/* Urgent Actionable Alert Banner for Complete Infrastructure Outage */}
      {backendOnline === false && (
        <div className="bg-red-50/90 border border-red-200/60 backdrop-blur-sm text-red-900 px-5 py-4 rounded-[12px] flex flex-col sm:flex-row items-start sm:items-center justify-between shadow-md border-l-4 border-l-red-500 transition-all duration-300">
          <div className="flex items-center gap-3 mb-3 sm:mb-0">
            <div className="bg-red-100 p-2 rounded-full text-red-600 animate-pulse">
              <span className="text-xl">📡</span>
            </div>
            <div>
              <h4 className="font-bold text-sm tracking-tight flex items-center gap-2 text-red-800">
                LOCAL GATEWAY OFFLINE
              </h4>
              <p className="text-xs text-red-700 mt-0.5">
                TigerGraph GraphRAG Engine at <code className="bg-red-100/80 px-1.5 py-0.5 font-mono text-red-800 rounded text-[10px]">http://localhost:8080</code> is unreachable.
              </p>
            </div>
          </div>
          <div className="flex flex-col items-end text-[11px] font-semibold">
            <span className="text-red-600 uppercase tracking-wider text-[10px] mb-1 font-bold opacity-80">Terminal Directive</span>
            <code className="bg-gray-900 text-emerald-400 px-3 py-1.5 rounded-[6px] font-mono border border-gray-800 shadow-inner">
              uvicorn main:app --port 8080
            </code>
          </div>
        </div>
      )}

      <div className="bg-white border border-[#f0f0f3] rounded-[12px] p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 relative overflow-hidden">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            System Ingestion Matrix
            
            {/* Real-Time Node Status Indicators */}
            {backendOnline === true && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                SYSTEM READY
              </span>
            )}
            
            {backendOnline === false && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-700 ring-1 ring-inset ring-rose-600/20 animate-pulse">
                <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                GATEWAY SHUTDOWN
              </span>
            )}

            {isBusy && (
              <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-bold text-blue-700 ring-1 ring-inset ring-blue-700/10 animate-pulse ml-1">
                SYNCING
              </span>
            )}
          </h3>
          <p className="text-sm text-gray-500">Deploy raw text corpuses into coordinated distributed vector-graph storage meshes.</p>
          {dbStats && (
            <div className="flex gap-4 mt-2 text-xs font-semibold text-gray-700 bg-gray-50 p-2 rounded-md border border-gray-100 w-fit">
               {dbStats.tokens !== undefined && (
                 <span>🔤 Indexed Tokens: <span className="text-gray-900 mx-1 bg-gray-200 px-1 py-0.5 rounded">{dbStats.tokens.toLocaleString()}</span></span>
               )}
               <span>📊 Vector Chunks Indexed: <span className="text-[#0d74ce]">{dbStats.vectors}</span></span>
               <span>📄 Graph Documents: <span className="text-purple-600">{dbStats.documents}</span></span>
               <span>🕸️ Graph Entities: <span className="text-amber-600">{dbStats.entities}</span></span>
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-4">
          {statusMsg && !isProcessing && (
            <span className={`text-sm font-medium ${
              uploadStatus === 'success' ? 'text-green-600' : 
              uploadStatus === 'error' ? 'text-red-600' : 
              'text-blue-600'
            }`}>
              {statusMsg}
            </span>
          )}

          <input 
            type="file" 
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.txt"
            multiple
            className="hidden" 
          />

          <div className="flex items-center gap-2">
            <button
              onClick={handleClearData}
              disabled={isBusy}
              title="Clear all databases to start fresh"
              className={`flex h-[40px] items-center justify-center gap-2 rounded-md px-3 text-sm font-semibold transition-all
                ${(isBusy) 
                  ? 'bg-gray-50 text-gray-300 border border-gray-200 cursor-not-allowed' 
                  : 'bg-white border border-gray-200 text-gray-500 hover:border-red-300 hover:text-red-600 hover:bg-red-50 shadow-sm active:scale-[0.98]'
                }`}
            >
              {isClearing ? (
                <svg className="animate-spin h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              )}
            </button>

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isBusy}
              className={`flex h-[40px] items-center justify-center gap-2 rounded-md px-6 text-sm font-semibold transition-all
                ${(isBusy) 
                  ? 'bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed' 
                  : 'bg-[#1a1a2e] border border-[#1a1a2e] text-white hover:bg-[#23233f] hover:border-[#23233f] shadow-sm active:scale-[0.98]'
                }`}
            >
              {isUploading || isProcessing ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {isUploading ? 'Uploading...' : 'Processing...'}
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  Feed Knowledge Corpus
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Live Progress Tracking Overlay */}
      {(isProcessing || logs.length > 0) && (
        <div className="bg-[#0B0E14] border border-[#1F2937] rounded-[12px] overflow-hidden transition-all animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="px-4 py-3 border-b border-[#1F2937] flex items-center justify-between bg-[#111827]">
            <div className="flex items-center gap-3">
              <div className={`h-2 w-2 rounded-full ${isProcessing ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
              <span className="text-xs font-mono font-bold tracking-wider text-gray-400 uppercase">Telemetry Stream: {progress}% Complete</span>
            </div>
            <div className="w-64 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-500 ease-out" 
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          
          <div 
            ref={logContainerRef}
            className="p-4 max-h-48 overflow-y-auto font-mono text-[13px] leading-relaxed space-y-1 bg-[#0d1117]"
          >
            {logs.length === 0 && (
              <div className="text-gray-600 italic">Awaiting payload initialization string...</div>
            )}
            {logs.map((log, idx) => (
              <div key={idx} className={`flex items-start gap-2 ${
                log.type === 'error' ? 'text-red-400' : 
                log.type === 'warning' ? 'text-yellow-400' : 
                log.type === 'complete' ? 'text-emerald-400 font-bold' : 
                'text-blue-300'
              }`}>
                <span className="opacity-40 select-none">[{String(idx + 1).padStart(3, '0')}]</span>
                <span>{log.msg}</span>
              </div>
            ))}
            {isProcessing && (
              <div className="text-blue-400/60 animate-pulse">▋ SYSTEM EXECUTING OPERATIONS...</div>
            )}
          </div>
          
          {/* Final Report Summary */}
          {uploadStatus === 'success' && !isProcessing && (
            <div className="px-4 py-2 bg-[#0f172a] border-t border-[#1e293b] text-xs text-blue-400 font-medium flex items-center justify-between">
              <span>🚀 Sync routine terminated successfully.</span>
              <button 
                onClick={() => { setLogs([]); setProgress(0); setUploadStatus('idle'); setStatusMsg(''); }}
                className="text-gray-500 hover:text-white transition-colors"
              >
                [DISMISS CONSOLE]
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
