import React from 'react';
import { act, renderHook } from '@testing-library/react';
import type { TConversation } from 'librechat-data-provider';
import type { SelectedValues } from '~/common';
import useSelectorEffects from '../useSelectorEffects';

const mockSetOption = jest.fn(() => jest.fn());
jest.mock('~/hooks/Conversations/useSetIndexOptions', () => () => ({ setOption: mockSetOption }));

function useSelection(conversation: TConversation) {
  const [selected, setSelectedValues] = React.useState<SelectedValues>({
    endpoint: '',
    model: '',
    modelSpec: '',
  });
  useSelectorEffects({
    conversation,
    agentsMap: undefined,
    assistantsMap: undefined,
    setSelectedValues,
  });
  return selected;
}

describe('model selection debounce', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  test('settles after the state update without scheduling a render loop', () => {
    const conversation = { endpoint: 'azureOpenAI', model: 'gpt-4o-mini' } as TConversation;
    const { result } = renderHook(() => useSelection(conversation));
    act(() => jest.advanceTimersByTime(150));
    expect(result.current.model).toBe('gpt-4o-mini');
    expect(jest.getTimerCount()).toBe(0);
  });

  test('switching models cancels the previous pending selection', () => {
    const { result, rerender } = renderHook(
      ({ model }) => useSelection({ endpoint: 'azureOpenAI', model } as TConversation),
      { initialProps: { model: 'gpt-4o-mini' } },
    );
    act(() => jest.advanceTimersByTime(100));
    rerender({ model: 'gpt-4o' });
    act(() => jest.advanceTimersByTime(150));
    expect(result.current.model).toBe('gpt-4o');
    expect(jest.getTimerCount()).toBe(0);
  });
});
