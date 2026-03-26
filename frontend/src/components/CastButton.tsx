interface Props {
  isAvailable: boolean;
  isConnected: boolean;
  deviceName: string | null;
  onClick: () => void;
}

export default function CastButton({
  isAvailable,
  isConnected,
  deviceName,
  onClick,
}: Props) {
  if (!isAvailable) return null;

  return (
    <button
      onClick={onClick}
      className={`w-9 h-9 shrink-0 rounded-full flex items-center justify-center
               transition-all cursor-pointer relative group
               ${
                 isConnected
                   ? "text-gold-light bg-gold/20"
                   : "text-gold-light/60 hover:text-gold-light hover:bg-gold/20"
               }`}
      title={
        isConnected ? `Casting to ${deviceName ?? "device"}` : "Cast"
      }
    >
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-[18px] h-[18px]">
        {isConnected ? (
          // Connected icon — filled receiver
          <>
            <path d="M1 18v3h3c0-1.66-1.34-3-3-3z" />
            <path d="M1 14v2c2.76 0 5 2.24 5 5h2c0-3.87-3.13-7-7-7z" />
            <path d="M1 10v2c4.97 0 9 4.03 9 9h2c0-6.08-4.93-11-11-11z" />
            <path d="M21 3H3c-1.1 0-2 .9-2 2v3h2V5h18v14h-7v2h7c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z" />
          </>
        ) : (
          // Disconnected icon — outline receiver
          <>
            <path d="M1 18v3h3c0-1.66-1.34-3-3-3z" />
            <path d="M1 14v2c2.76 0 5 2.24 5 5h2c0-3.87-3.13-7-7-7z" />
            <path d="M1 10v2c4.97 0 9 4.03 9 9h2c0-6.08-4.93-11-11-11z" />
            <path d="M21 3H3c-1.1 0-2 .9-2 2v3h2V5h18v14h-7v2h7c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z" />
          </>
        )}
      </svg>

      {/* Tooltip showing device name */}
      {isConnected && deviceName && (
        <span
          className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 whitespace-nowrap
                     bg-black/90 text-white text-[10px] px-2 py-1 rounded
                     opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
        >
          {deviceName}
        </span>
      )}
    </button>
  );
}
