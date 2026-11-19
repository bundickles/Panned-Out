
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import { getRecipes } from "../../api/recipes";

import "./AIPhoto.css";

const MAX_PHOTO_SIZE = 10 * 1024 * 1024;
const SUPPORTED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
];

export default function AIPhoto() {
  const [photo, setPhoto] = useState(null);
  const [photoError, setPhotoError] = useState("");
  const [cameraError, setCameraError] = useState("");
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraBusy, setCameraBusy] = useState(false);

  const [ingredients, setIngredients] = useState("");
  const [matches, setMatches] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const videoRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);
  const mountedRef = useRef(true);

  // Stop the camera whenever the user leaves the page.
  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;

      streamRef.current
        ?.getTracks()
        .forEach((track) => track.stop());

      streamRef.current = null;
    };
  }, []);

  // Clean up old image previews.
  useEffect(() => {
    return () => {
      if (photo?.url) {
        URL.revokeObjectURL(photo.url);
      }
    };
  }, [photo]);

  // Attach the live camera stream to the video element.
  useEffect(() => {
    const video = videoRef.current;

    if (cameraOpen && video && streamRef.current) {
      video.srcObject = streamRef.current;

      video.play().catch(() => {
        setCameraError(
          "Camera preview could not start."
        );
      });
    }
  }, [cameraOpen]);

  // Validate and preview a selected photo.
  function choosePhoto(file) {
    if (!file) return;

    if (!SUPPORTED_TYPES.includes(file.type)) {
      setPhotoError(
        "Choose a JPEG, PNG, or WebP image."
      );
      return;
    }

    if (file.size > MAX_PHOTO_SIZE) {
      setPhotoError(
        "Choose an image smaller than 10 MB."
      );
      return;
    }

    setPhotoError("");

    if (cameraOpen) {
      stopCamera();
    }

    setPhoto({
      url: URL.createObjectURL(file),
      name: file.name,
    });
  }

  // Release the camera.
  function stopCamera() {
    streamRef.current
      ?.getTracks()
      .forEach((track) => track.stop());

    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraOpen(false);
  }

  // Request webcam access.
  async function startCamera() {
    setCameraError("");

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(
        "Camera access requires a supported browser on HTTPS or localhost."
      );
      return;
    }

    setCameraBusy(true);

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
          },
          audio: false,
        });

      if (!mountedRef.current) {
        stream
          .getTracks()
          .forEach((track) => track.stop());

        return;
      }

      streamRef.current = stream;
      setCameraOpen(true);
    } catch {
      if (mountedRef.current) {
        setCameraError(
          "Could not access your camera. Check browser permissions or upload a photo instead."
        );
      }
    } finally {
      if (mountedRef.current) {
        setCameraBusy(false);
      }
    }
  }

  // Capture a photo from the live webcam preview.
  function capturePhoto() {
    const video = videoRef.current;

    if (!video?.videoWidth || !video?.videoHeight) {
      setCameraError(
        "Camera is still loading. Try again in a moment."
      );
      return;
    }

    const canvas = document.createElement("canvas");

    const scale = Math.min(
      1,
      1280 / video.videoWidth
    );

    canvas.width = Math.round(
      video.videoWidth * scale
    );

    canvas.height = Math.round(
      video.videoHeight * scale
    );

    canvas
      .getContext("2d")
      ?.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
      );

    canvas.toBlob(
      (blob) => {
        if (!mountedRef.current) return;

        if (!blob) {
          setCameraError(
            "Unable to capture an image. Please try again."
          );
          return;
        }

        choosePhoto(
          new File(
            [blob],
            "kitchen-photo.jpg",
            { type: "image/jpeg" }
          )
        );
      },
      "image/jpeg",
      0.85
    );
  }

  // Search saved recipes using typed ingredients.
  // This is keyword matching, NOT image AI.
  async function searchByIngredients(event) {
    event.preventDefault();

    const terms = [
      ...new Set(
        ingredients
          .split(/[,;\n]+/)
          .map((value) =>
            value.trim().toLowerCase()
          )
          .filter(Boolean)
      ),
    ];

    if (!terms.length) {
      setSearchError(
        "Enter at least one ingredient, separated by commas."
      );
      setMatches(null);
      return;
    }

    setSearching(true);
    setSearchError("");
    setMatches(null);

    try {
      const recipes = await getRecipes();

      const ranked = recipes
        .map((recipe) => {
          const text = String(
            recipe.ingredients ?? ""
          ).toLowerCase();

          const matched = terms.filter(
            (term) => text.includes(term)
          );

          return { recipe, matched };
        })
        .filter(
          (item) => item.matched.length > 0
        )
        .sort(
          (a, b) =>
            b.matched.length - a.matched.length
        )
        .slice(0, 6);

      setMatches(ranked);
    } catch (error) {
      setSearchError(
        error.message ||
          "Unable to search recipes."
      );
    } finally {
      setSearching(false);
    }
  }

  return (
    <main className="ai-photo-page">
      <Sidebar />

      <div className="ai-photo-content">
        <div className="ai-photo-container">

          {/* WELCOME BANNER */}

          <header className="ai-photo-hero">
            <div>
              <span className="ai-photo-eyebrow">
                PANNED OUT / KITCHEN STUDIO
              </span>

              <h1>What could we cook?</h1>

              <p>
                Give your ingredients a moment
                in the spotlight. Upload a photo,
                take one with your camera, or
                search your recipes by ingredient.
              </p>
            </div>

            <div
              className="ai-photo-hero-art"
              aria-hidden="true"
            >
              ✳
            </div>
          </header>

          <div className="ai-photo-grid">

            {/* PHOTO INPUT PANEL */}

            <section
              className="ai-photo-panel"
              aria-labelledby="ai-photo-title"
            >
              <div className="ai-photo-panel-heading">
                <span className="ai-photo-step">
                  01 / THE PHOTO
                </span>

                <h2 id="ai-photo-title">
                  Show us your ingredients
                </h2>

                <p>
                  For now, photos are previewed
                  only in your browser. AI image
                  recognition will be connected
                  in a future backend integration.
                </p>
              </div>

              <div className="ai-photo-dropzone">
                {cameraOpen ? (
                  <video
                    ref={videoRef}
                    className="ai-photo-preview"
                    autoPlay
                    muted
                    playsInline
                    aria-label="Live camera preview"
                  />
                ) : photo ? (
                  <img
                    className="ai-photo-preview"
                    src={photo.url}
                    alt={`Selected photo: ${photo.name}`}
                  />
                ) : (
                  <div className="ai-photo-empty">
                    <span
                      className="ai-photo-empty-mark"
                      aria-hidden="true"
                    >
                      ▧
                    </span>

                    <strong>
                      Your kitchen, your canvas
                    </strong>

                    <span>
                      JPEG, PNG or WebP · up to 10 MB
                    </span>
                  </div>
                )}
              </div>

              <div className="ai-photo-controls">

                <button
                  className="ai-photo-button ai-photo-button-primary"
                  type="button"
                  onClick={() =>
                    fileInputRef.current?.click()
                  }
                >
                  Upload photo
                </button>

                <input
                  ref={fileInputRef}
                  tabIndex={-1}
                  id="ai-photo-upload"
                  className="ai-photo-file-input"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => {
                    choosePhoto(
                      event.target.files?.[0]
                    );

                    event.target.value = "";
                  }}
                />

                {cameraOpen ? (
                  <>
                    <button
                      className="ai-photo-button ai-photo-button-primary"
                      type="button"
                      onClick={capturePhoto}
                    >
                      Capture photo
                    </button>

                    <button
                      className="ai-photo-button"
                      type="button"
                      onClick={stopCamera}
                    >
                      Stop camera
                    </button>
                  </>
                ) : (
                  <button
                    className="ai-photo-button"
                    type="button"
                    disabled={cameraBusy}
                    onClick={startCamera}
                  >
                    {cameraBusy
                      ? "Connecting…"
                      : "Use camera"}
                  </button>
                )}

                {photo && !cameraOpen && (
                  <button
                    className="ai-photo-button ai-photo-button-quiet"
                    type="button"
                    onClick={() => setPhoto(null)}
                  >
                    Remove photo
                  </button>
                )}
              </div>

              {photoError && (
                <p
                  role="alert"
                  className="ai-photo-error"
                >
                  {photoError}
                </p>
              )}

              {cameraError && (
                <p
                  role="alert"
                  className="ai-photo-error"
                >
                  {cameraError}
                </p>
              )}

              {photo && !cameraOpen && (
                <p
                  className="ai-photo-ready"
                  role="status"
                >
                  Photo ready: {photo.name}.
                  It has not been uploaded or
                  analyzed.
                </p>
              )}

              <div className="ai-photo-coming-soon">
                <span
                  className="ai-photo-coming-soon-mark"
                  aria-hidden="true"
                >
                  ✦
                </span>

                <div>
                  <strong>
                    AI photo recognition is the
                    next connection
                  </strong>

                  <p>
                    A future endpoint will identify
                    ingredients in your photo and
                    suggest recipes. No photo is
                    sent to a server in this version.
                  </p>
                </div>
              </div>
            </section>

            {/* RECIPE SEARCH PANEL */}

            <div className="ai-photo-side">
              <section
                className="ai-photo-panel"
                aria-labelledby="ai-ingredients-title"
              >
                <span className="ai-photo-step">
                  02 / TRY IT NOW
                </span>

                <h2 id="ai-ingredients-title">
                  Find a recipe by ingredient
                </h2>

                <p>
                  This is a simple keyword search
                  of your saved recipes—not AI
                  photo recognition.
                </p>

                <form
                  onSubmit={searchByIngredients}
                  className="ai-photo-search-form"
                >
                  <label htmlFor="ai-ingredient-input">
                    Ingredients you have
                  </label>

                  <textarea
                    id="ai-ingredient-input"
                    rows={3}
                    value={ingredients}
                    onChange={(event) =>
                      setIngredients(event.target.value)
                    }
                    placeholder="e.g. tomatoes, eggs, spinach"
                  />

                  <button
                    className="ai-photo-button ai-photo-button-primary"
                    type="submit"
                    disabled={searching}
                  >
                    {searching
                      ? "Finding recipes…"
                      : "Find matching recipes"}
                  </button>
                </form>

                {searchError && (
                  <p
                    className="ai-photo-error"
                    role="alert"
                  >
                    {searchError}
                  </p>
                )}

                {matches !== null && (
                  <div
                    className="ai-photo-results"
                    aria-live="polite"
                  >
                    <h3>
                      {matches.length
                        ? "Possible matches"
                        : "No matches yet"}
                    </h3>

                    {!matches.length && (
                      <p>
                        Try different ingredients
                        or create a recipe first.
                      </p>
                    )}

                    {matches.map(
                      ({ recipe, matched }) => (
                        <Link
                          key={recipe.id}
                          to={`/recipes/${encodeURIComponent(
                            recipe.id
                          )}`}
                          className="ai-photo-recipe-link"
                        >
                          <strong>
                            {recipe.name}
                          </strong>

                          <span>
                            {matched.length} matching
                            ingredient
                            {matched.length === 1
                              ? ""
                              : "s"}{" "}
                            · View recipe
                          </span>
                        </Link>
                      )
                    )}
                  </div>
                )}
              </section>

              {/* RECIPES SHORTCUT */}

              <section className="ai-photo-recipes-panel">
                <span className="ai-photo-step">
                  YOUR RECIPE BOOK
                </span>

                <h2>
                  Already have something in mind?
                </h2>

                <p>
                  Explore your recipe collection
                  or add something new before
                  you start planning meals.
                </p>

                <Link
                  className="ai-photo-button ai-photo-button-primary"
                  to="/recipes"
                >
                  Browse all recipes
                </Link>
              </section>
            </div>

          </div>
        </div>
      </div>
    </main>
  );
}
