import type { StoryType } from "../types";

interface Props {
  onSelect: (type: StoryType) => void;
}

export default function StoryTypeSelector({ onSelect }: Props) {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-3xl font-bold text-center text-purple-700">
        Choose your adventure
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <button
          onClick={() => onSelect("custom")}
          className="p-8 border-3 border-purple-200 rounded-2xl hover:border-purple-500 hover:shadow-lg transition-all text-left group"
        >
          <div className="text-5xl mb-4">✨</div>
          <h3 className="text-xl font-bold text-purple-700 group-hover:text-purple-800">
            Custom Story
          </h3>
          <p className="text-gray-600 mt-2">
            Create your own adventure — pick a genre and describe your story idea.
          </p>
        </button>

        <button
          onClick={() => onSelect("historical")}
          className="p-8 border-3 border-amber-200 rounded-2xl hover:border-amber-500 hover:shadow-lg transition-all text-left group"
        >
          <div className="text-5xl mb-4">🏛️</div>
          <h3 className="text-xl font-bold text-amber-700 group-hover:text-amber-800">
            Historical Adventure
          </h3>
          <p className="text-gray-600 mt-2">
            Travel through time and witness amazing moments in history.
          </p>
        </button>
      </div>
    </div>
  );
}
