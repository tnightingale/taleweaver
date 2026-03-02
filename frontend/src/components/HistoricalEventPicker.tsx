import { useEffect, useState } from "react";
import type { HistoricalEvent } from "../types";
import { fetchHistoricalEvents } from "../api/client";

interface Props {
  onSelect: (eventId: string) => void;
  onBack: () => void;
}

export default function HistoricalEventPicker({ onSelect, onBack }: Props) {
  const [events, setEvents] = useState<HistoricalEvent[]>([]);

  useEffect(() => {
    fetchHistoricalEvents().then(setEvents);
  }, []);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-3xl font-bold text-center text-amber-700">
        Pick a moment in history
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {events.map((event) => (
          <button
            key={event.id}
            onClick={() => onSelect(event.id)}
            className="p-6 border-2 border-amber-200 rounded-xl hover:border-amber-500 hover:shadow-lg transition-all text-left"
          >
            <div className="flex justify-between items-start">
              <h3 className="font-bold text-amber-800">{event.title}</h3>
              <span className="text-sm text-amber-600 font-mono ml-2">
                {event.year > 0 ? event.year : `${Math.abs(event.year)} BC`}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-1">{event.figure}</p>
            <p className="text-sm text-gray-500 mt-2">{event.summary}</p>
          </button>
        ))}
      </div>

      <button
        onClick={onBack}
        className="px-6 py-3 border-2 border-gray-300 rounded-xl hover:bg-gray-50 transition-colors"
      >
        Back
      </button>
    </div>
  );
}
