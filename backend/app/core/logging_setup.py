import logging
from rich.logging import RichHandler
from app.core.config import settings

def setup_rich_logging():
    """
    Configures terminal logging using the installed 'rich' library handlers.
    Injects structural syntax highlighting and stylized traceback formatting.
    """
    log_level = "DEBUG" if settings.TESTING else "INFO"
    
    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_path=False,
                omit_repeated_times=False,
            )
        ],
    )

    # Adjust verbosity of common noisy dependencies
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    
    # Keep application level logs healthy
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    
    # Inform operators that telemetry is armed
    logging.getLogger("app.core").info(f"🚀 [bold cyan]Visual Telemetry Deck Powered by Rich[/bold cyan] | Log Level: [green]{log_level}[/green]")
