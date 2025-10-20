import { render, screen } from '@testing-library/react';
import WelcomeMessage from './welcome-message';

describe('WelcomeMessage', () => {
  it('renders the welcome message', () => {
    render(<WelcomeMessage />);
    expect(screen.getByText('Welcome to AgenticFleet')).toBeInTheDocument();
  });
});
