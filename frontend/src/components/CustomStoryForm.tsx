import { useEffect, useState } from "react";
import type { Genre } from "../types";
import { fetchGenres } from "../api/client";

interface Props {
  onSubmit: (genre: string, description: string) => void;
  onBack: () => void;
}

export default function CustomStoryForm({ onSubmit, onBack }: Props) {
  const [genres, setGenres] = useState<Genre[]>([]);
  const [selectedGenre, setSelectedGenre] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    fetchGenres().then(setGenres);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(selectedGenre, description);
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-3xl font-bold text-center text-purple-700">
        Design your story
      </h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Pick a genre
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {genres.map((genre) => (
            <button
              key={genre.id}
              type="button"
              onClick={() => setSelectedGenre(genre.id)}
              className={`p-4 rounded-xl border-2 text-left transition-all ${
                selectedGenre === genre.id
                  ? "border-purple-500 bg-purple-50"
                  : "border-gray-200 hover:border-purple-300"
              }`}
            >
              <div className="text-2xl">{genre.icon}</div>
              <div className="font-semibold mt-1">{genre.name}</div>
              <div className="text-xs text-gray-500">{genre.description}</div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          What should the story be about?
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          rows={3}
          className="w-full px-4 py-2 border-2 border-purple-200 rounded-xl focus:border-purple-500 focus:outline-none"
          placeholder="A magical paintbrush that brings drawings to life..."
        />
      </div>

      <div className="flex gap-4">
        <button
          type="button"
          onClick={onBack}
          className="px-6 py-3 border-2 border-gray-300 rounded-xl hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          type="submit"
          disabled={!selectedGenre || !description}
          className="flex-1 py-3 bg-purple-600 text-white font-bold rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Create Story
        </button>
      </div>
    </form>
  );
}
