// Story Spring Custom Chromecast Receiver
// Displays scene illustrations fullscreen, synced to audio playback

interface SceneData {
  image_url: string | null;
  beat_name: string;
  timestamp_start: number;
  timestamp_end: number;
}

interface CustomData {
  scenes?: SceneData[];
  title?: string;
}

const context = cast.framework.CastReceiverContext.getInstance();
const playerManager = context.getPlayerManager();

// DOM elements
const sceneImage = document.getElementById("scene-image") as HTMLImageElement;
const storyTitle = document.getElementById("story-title")!;
const chapterTitle = document.getElementById("chapter-title")!;
const titleBar = document.getElementById("title-bar")!;
const progressFill = document.getElementById("progress-fill")!;
const idleScreen = document.getElementById("idle-screen")!;
const illustration = document.getElementById("illustration")!;

let scenes: SceneData[] = [];
let currentSceneIndex = -1;
let titleHideTimer: ReturnType<typeof setTimeout> | null = null;

// When media is loaded, extract scene data from customData
playerManager.setMessageInterceptor(
  cast.framework.messages.MessageType.LOAD,
  (request) => {
    const customData = request.media?.customData as CustomData | undefined;

    if (customData?.scenes) {
      scenes = customData.scenes;
    } else {
      scenes = [];
    }

    currentSceneIndex = -1;

    // Set story title
    const title = customData?.title || request.media?.metadata?.title || "";
    storyTitle.textContent = title;

    // Hide idle screen
    idleScreen.classList.add("hidden");
    titleBar.classList.add("visible");

    // Show title for 5s then hide
    showTitleBar();

    return request;
  }
);

// Track playback time and update scene
playerManager.addEventListener(
  cast.framework.events.EventType.TIME_UPDATE,
  (event) => {
    if (!("currentMediaTime" in event)) return;
    const time = (event as cast.framework.events.MediaElementEvent)
      .currentMediaTime;
    if (time == null) return;

    updateScene(time);
    updateProgress(time);
  }
);

// When playback ends, show title bar
playerManager.addEventListener(
  cast.framework.events.EventType.MEDIA_FINISHED,
  () => {
    titleBar.classList.add("visible");
    if (titleHideTimer) clearTimeout(titleHideTimer);
  }
);

// When playback resumes after pause, briefly show title
playerManager.addEventListener(
  cast.framework.events.EventType.PLAYING,
  () => {
    showTitleBar();
  }
);

function updateScene(time: number) {
  if (scenes.length === 0) return;

  const newIndex = scenes.findIndex(
    (s) => time >= s.timestamp_start && time < s.timestamp_end
  );

  if (newIndex === -1 || newIndex === currentSceneIndex) return;

  const scene = scenes[newIndex];
  currentSceneIndex = newIndex;

  // Update chapter title
  chapterTitle.textContent = `Chapter ${newIndex + 1} of ${scenes.length}: ${scene.beat_name}`;
  showTitleBar();

  // Crossfade to new image
  if (scene.image_url) {
    crossfadeToImage(scene.image_url);
  } else {
    // No image — fade out
    sceneImage.classList.remove("visible");
  }
}

function crossfadeToImage(url: string) {
  // Create outgoing clone of current image
  if (sceneImage.classList.contains("visible") && sceneImage.src) {
    const outgoing = sceneImage.cloneNode(true) as HTMLImageElement;
    outgoing.classList.remove("visible");
    outgoing.classList.add("outgoing");
    outgoing.style.opacity = "1";
    illustration.appendChild(outgoing);

    // Fade out and remove
    requestAnimationFrame(() => {
      outgoing.style.opacity = "0";
      outgoing.addEventListener("transitionend", () => outgoing.remove(), {
        once: true,
      });
    });
  }

  // Preload new image then show
  const preload = new Image();
  preload.onload = () => {
    sceneImage.classList.remove("visible");
    sceneImage.src = url;
    // Force reflow for transition
    void sceneImage.offsetWidth;
    sceneImage.classList.add("visible");
  };
  preload.src = url;
}

function updateProgress(time: number) {
  const duration = playerManager.getDurationSec();
  if (duration && duration > 0) {
    const pct = Math.min(100, (time / duration) * 100);
    progressFill.style.width = `${pct}%`;
  }
}

function showTitleBar() {
  titleBar.classList.add("visible");
  if (titleHideTimer) clearTimeout(titleHideTimer);
  titleHideTimer = setTimeout(() => {
    titleBar.classList.remove("visible");
  }, 5000);
}

// Start the receiver
context.start();
