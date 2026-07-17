# Common Pitfalls and Accessibility Testing

Detail for `testing-obsessive`.

## Common Pitfalls

### Over-Mocking
```typescript
// ✗ Bad: Mocking everything, testing nothing
it('should update user', async () => {
  vi.mock('./updateUser');
  const result = await updateUser(user);
  expect(result).toBeDefined(); // What are we even testing?
});

// ✓ Good: Test real code, mock external dependencies
it('should update user', async () => {
  const mockFetch = vi.fn().mockResolvedValue({ ok: true });
  global.fetch = mockFetch;
  
  const result = await updateUser(user);
  
  expect(mockFetch).toHaveBeenCalledWith('/api/users/1', {
    method: 'PUT',
    body: JSON.stringify(user)
  });
  expect(result.success).toBe(true);
});
```

### Testing Implementation Details
```typescript
// ✗ Bad: Testing internal state
it('should set loading to true', () => {
  const { component } = render(UserList);
  expect(component.loading).toBe(true); // Internal detail
});

// ✓ Good: Testing observable behaviour
it('should show loading indicator', () => {
  render(UserList);
  expect(screen.getByText('Loading...')).toBeInTheDocument();
});
```

### Brittle Selectors
```typescript
// ✗ Bad: Fragile selectors
const button = container.querySelector('.btn.btn--primary.large');

// ✓ Good: Semantic queries
const button = screen.getByRole('button', { name: 'Submit' });
```

### Not Testing Error Cases
```typescript
// ✗ Bad: Only happy path
it('should fetch user', async () => {
  const user = await fetchUser('1');
  expect(user).toBeDefined();
});

// ✓ Good: Test errors too
describe('fetchUser', () => {
  it('should return user on success', async () => {
    const user = await fetchUser('1');
    expect(user.id).toBe('1');
  });

  it('should throw on network error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
    
    await expect(fetchUser('1')).rejects.toThrow('Network error');
  });

  it('should return null when user not found', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404
    });
    
    const user = await fetchUser('999');
    expect(user).toBeNull();
  });
});
```

## Accessibility Testing

Accessibility is a testable requirement, not a subjective preference. Include it in the testing strategy alongside functional tests.

### Automated Accessibility Checks
```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('should have no accessibility violations', async () => {
	const { container } = render(LoginForm);
	const results = await axe(container);
	expect(results).toHaveNoViolations();
});
```

### Keyboard Navigation Tests
```typescript
it('should be navigable by keyboard', async () => {
	render(LoginForm);

	// Tab to email input
	await userEvent.tab();
	expect(screen.getByLabelText('Email')).toHaveFocus();

	// Tab to password input
	await userEvent.tab();
	expect(screen.getByLabelText('Password')).toHaveFocus();

	// Tab to submit button
	await userEvent.tab();
	expect(screen.getByRole('button', { name: /log in/i })).toHaveFocus();

	// Enter submits
	await userEvent.keyboard('{Enter}');
	// Assert form submitted
});
```

### Screen Reader Assertions
```typescript
it('should announce errors to screen readers', async () => {
	render(LoginForm);

	const submitButton = screen.getByRole('button', { name: /log in/i });
	await fireEvent.click(submitButton);

	// Error messages should be associated with inputs
	const emailInput = screen.getByLabelText('Email');
	const errorId = emailInput.getAttribute('aria-describedby');
	expect(errorId).toBeTruthy();
	expect(document.getElementById(errorId)).toHaveTextContent('Email is required');
});
```

### What to Test for Accessibility
```
HIGH PRIORITY:
✓ Forms: labels, error association, keyboard submit
✓ Modals: focus trap, escape to close, focus return
✓ Navigation: keyboard traversal, skip links
✓ Dynamic content: aria-live announcements

MEDIUM PRIORITY:
✓ Colour contrast (automated via axe)
✓ Image alt text presence
✓ Heading hierarchy

AUTOMATED (run on every component):
✓ axe-core violations check
```
