// frontend/src/components/KidProfileForm.tsx
import { useState } from "react";
import type { KidProfile } from "../types";

interface Props {
  onSubmit: (profile: KidProfile) => void;
}

const PERSONALITIES = ["adventurous", "curious", "shy", "funny"];

export default function KidProfileForm({ onSubmit }: Props) {
  const [name, setName] = useState("");
  const [age, setAge] = useState(7);
  const [favoriteAnimal, setFavoriteAnimal] = useState("");
  const [favoriteColor, setFavoriteColor] = useState("");
  const [hobby, setHobby] = useState("");
  const [bestFriend, setBestFriend] = useState("");
  const [petName, setPetName] = useState("");
  const [personality, setPersonality] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const profile: KidProfile = {
      name,
      age,
      ...(favoriteAnimal && { favorite_animal: favoriteAnimal }),
      ...(favoriteColor && { favorite_color: favoriteColor }),
      ...(hobby && { hobby }),
      ...(bestFriend && { best_friend: bestFriend }),
      ...(petName && { pet_name: petName }),
      ...(personality && { personality }),
    };
    onSubmit(profile);
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-lg mx-auto space-y-6">
      <h2 className="text-3xl font-bold text-center text-purple-700">
        Tell us about your child
      </h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Name *
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="w-full px-4 py-2 border-2 border-purple-200 rounded-xl focus:border-purple-500 focus:outline-none"
          placeholder="Your child's name"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Age *
        </label>
        <select
          value={age}
          onChange={(e) => setAge(Number(e.target.value))}
          className="w-full px-4 py-2 border-2 border-purple-200 rounded-xl focus:border-purple-500 focus:outline-none"
        >
          {Array.from({ length: 10 }, (_, i) => i + 3).map((a) => (
            <option key={a} value={a}>{a} years old</option>
          ))}
        </select>
      </div>

      <div className="border-t border-gray-200 pt-4">
        <p className="text-sm text-gray-500 mb-3">
          Optional details (makes the story more personal)
        </p>
        <div className="grid grid-cols-2 gap-4">
          <input
            type="text"
            value={favoriteAnimal}
            onChange={(e) => setFavoriteAnimal(e.target.value)}
            className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
            placeholder="Favorite animal"
          />
          <input
            type="text"
            value={favoriteColor}
            onChange={(e) => setFavoriteColor(e.target.value)}
            className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
            placeholder="Favorite color"
          />
          <input
            type="text"
            value={hobby}
            onChange={(e) => setHobby(e.target.value)}
            className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
            placeholder="Hobby"
          />
          <input
            type="text"
            value={bestFriend}
            onChange={(e) => setBestFriend(e.target.value)}
            className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
            placeholder="Best friend's name"
          />
          <input
            type="text"
            value={petName}
            onChange={(e) => setPetName(e.target.value)}
            className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
            placeholder="Pet's name"
          />
          <select
            value={personality}
            onChange={(e) => setPersonality(e.target.value)}
            className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
          >
            <option value="">Personality</option>
            {PERSONALITIES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>

      <button
        type="submit"
        disabled={!name}
        className="w-full py-3 bg-purple-600 text-white font-bold rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </form>
  );
}
