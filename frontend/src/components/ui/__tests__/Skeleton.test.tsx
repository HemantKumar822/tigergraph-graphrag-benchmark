import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Skeleton } from '../Skeleton';

describe('Skeleton Primitive', () => {
  it('renders correctly with default classes', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass('animate-pulse');
    expect(container.firstChild).toHaveClass('bg-[#f0f0f3]');
    expect(container.firstChild).toHaveClass('rounded-md');
  });

  it('accepts additional className props', () => {
    const { container } = render(<Skeleton className="w-10 h-10" />);
    expect(container.firstChild).toHaveClass('w-10');
    expect(container.firstChild).toHaveClass('h-10');
  });
});
