import { render, screen } from '@testing-library/react';
import PendingApprovals from './pending-approvals';

describe('PendingApprovals', () => {
  it('renders the pending approvals', () => {
    const pendingApprovals = [
      {
        requestId: '1',
        functionCall: {
          id: '1',
          name: 'test-function',
          arguments: {},
        },
      },
    ];
    render(
      <PendingApprovals
        pendingApprovals={pendingApprovals}
        approvalStatuses={{}}
        onRespondToApproval={() => {}}
      />
    );
    expect(screen.getByText('Pending approvals')).toBeInTheDocument();
  });
});
