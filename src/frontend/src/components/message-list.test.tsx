import { render, screen } from '@testing-library/react';
import MessageList from './message-list';

describe('MessageList', () => {
  it('renders the messages', () => {
    const messages = [
      {
        id: '1',
        role: 'user' as const,
        content: 'Hello',
        timestamp: Date.now(),
      },
    ];
    render(<MessageList messages={messages} isLoading={false} error={null} />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
