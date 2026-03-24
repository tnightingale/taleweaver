import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

// Mock auth context so App can render without a real AuthProvider
vi.mock('./contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'test-user', email: 'test@test.com', display_name: 'Test' },
    loading: false,
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
  }),
}));

const mockCreateCustomStory = vi.fn();
const mockCreateHistoricalStory = vi.fn();
const mockPollJobStatus = vi.fn();

vi.mock('./api/client', () => ({
  fetchGenres: vi.fn(() => Promise.resolve([
    { id: 'adventure', name: 'Adventure', description: 'Exciting journeys', icon: '🗺️' },
  ])),
  fetchHistoricalEvents: vi.fn(() => Promise.resolve([
    { id: 'moon', title: 'Moon Landing', figure: 'Neil Armstrong', year: 1969, summary: 'First on Moon', key_facts: [], thumbnail: '' },
  ])),
  fetchArtStyles: vi.fn(() => Promise.resolve([])),
  fetchRecentJobs: vi.fn(() => Promise.resolve({ jobs: [] })),
  createCustomStory: (...args: unknown[]) => mockCreateCustomStory(...args),
  createHistoricalStory: (...args: unknown[]) => mockCreateHistoricalStory(...args),
  pollJobStatus: (...args: unknown[]) => mockPollJobStatus(...args),
  getAudioUrl: vi.fn((id: string) => `/api/story/audio/${id}`),
  retryJob: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  mockCreateCustomStory.mockResolvedValue({ job_id: 'test-123', status: 'processing', stages: ['writing'], current_stage: 'writing' });
  mockCreateHistoricalStory.mockResolvedValue({ job_id: 'test-456', status: 'processing', stages: ['writing'], current_stage: 'writing' });
  mockPollJobStatus.mockResolvedValue({ job_id: 'test-123', status: 'processing', current_stage: 'writing', progress: 0, total_segments: 0 });
});

describe('App', () => {
  it('renders hero screen by default', () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByText('Taleweaver')).toBeInTheDocument();
    expect(screen.getByText("Who's the hero?")).toBeInTheDocument();
  });

  it('navigates to craft screen after submitting hero', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><App /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText("Your child's name"), 'Arjun');
    await user.click(screen.getByRole('button', { name: '7' }));
    await user.click(screen.getByRole('button', { name: /Custom Story/i }));

    await waitFor(() => {
      expect(screen.getByText('Craft the Adventure')).toBeInTheDocument();
    });
  });

  it('goes back from craft to hero', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><App /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText("Your child's name"), 'Arjun');
    await user.click(screen.getByRole('button', { name: '7' }));
    await user.click(screen.getByRole('button', { name: /Custom Story/i }));

    await waitFor(() => expect(screen.getByText('Craft the Adventure')).toBeInTheDocument());

    const backBtn = screen.getAllByRole('button').find(b => b.textContent?.includes('Back'));
    if (backBtn) await user.click(backBtn);

    await waitFor(() => expect(screen.getByText("Who's the hero?")).toBeInTheDocument());
  });

  it('shows error when custom story creation fails', async () => {
    mockCreateCustomStory.mockRejectedValueOnce(new Error('Network error'));
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    const user = userEvent.setup();
    render(<MemoryRouter><App /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText("Your child's name"), 'Arjun');
    await user.click(screen.getByRole('button', { name: '7' }));
    await user.click(screen.getByRole('button', { name: /Custom Story/i }));

    await waitFor(() => expect(screen.getByText('Adventure')).toBeInTheDocument());
    await user.click(screen.getByText('Adventure'));
    await user.type(screen.getByPlaceholderText('Describe your story idea...'), 'Magic');
    await user.click(screen.getByText('Create Story'));

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith('Network error');
    });
    alertSpy.mockRestore();
  });

  it('transitions to story screen on successful creation', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><App /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText("Your child's name"), 'Arjun');
    await user.click(screen.getByRole('button', { name: '7' }));
    await user.click(screen.getByRole('button', { name: /Custom Story/i }));

    await waitFor(() => expect(screen.getByText('Adventure')).toBeInTheDocument());
    await user.click(screen.getByText('Adventure'));
    await user.type(screen.getByPlaceholderText('Describe your story idea...'), 'Magic');
    await user.click(screen.getByText('Create Story'));

    await waitFor(() => {
      expect(mockCreateCustomStory).toHaveBeenCalled();
    });
  });

  it('navigates to historical and creates story', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><App /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText("Your child's name"), 'Arjun');
    await user.click(screen.getByRole('button', { name: '7' }));
    await user.click(screen.getByRole('button', { name: /Historical Adventure/i }));

    await waitFor(() => expect(screen.getByText('Moon Landing')).toBeInTheDocument());
    await user.click(screen.getByText('Moon Landing'));

    await waitFor(() => {
      expect(mockCreateHistoricalStory).toHaveBeenCalled();
      const call = mockCreateHistoricalStory.mock.calls[0];
      expect(call[1]).toBe('moon'); // event_id
    });
  });

  it('shows error when historical story creation fails', async () => {
    mockCreateHistoricalStory.mockRejectedValueOnce(new Error('Server error'));
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    const user = userEvent.setup();
    render(<MemoryRouter><App /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText("Your child's name"), 'Arjun');
    await user.click(screen.getByRole('button', { name: '7' }));
    await user.click(screen.getByRole('button', { name: /Historical Adventure/i }));

    await waitFor(() => expect(screen.getByText('Moon Landing')).toBeInTheDocument());
    await user.click(screen.getByText('Moon Landing'));

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith('Server error');
    });
    alertSpy.mockRestore();
  });
});
