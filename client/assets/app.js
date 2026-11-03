
"use strict";

/*
============================================================
DAVISN PRO 2.0 — WEB FRONTEND
============================================================
*/

const API_BASE = window.location.origin;

let currentMode = "cloud";
let isListening = false;
let recognition = null;
let cameraStream = null;
let faceDetectionTimer = null;

const $ = (id) => document.getElementById(id);

const messages = $("messages");
const input = $("messageInput");
const orb = $("orb");
const orbStatus = $("orbStatus");


/* ============================================================
   CHAT INTERFACE
============================================================ */

function addMessage(text, type = "system") {
    if (!messages) return;

    const message = document.createElement("div");
    message.className = "message " + type;
    message.textContent = text;

    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}

function setOrbState(state) {
    if (orbStatus) {
        orbStatus.textContent = state.toUpperCase();
    }

    if (orb) {
        orb.className = "orb " + state;
    }
}


/* ============================================================
   SPEECH OUTPUT
============================================================ */

function speak(text) {
    if (!window.speechSynthesis || !text) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    utterance.rate = 1;
    utterance.pitch = 0.9;

    window.speechSynthesis.speak(utterance);
}


/* ============================================================
   AI CHAT
============================================================ */

async function sendMessage() {
    if (!input) return;

    const message = input.value.trim();

    if (!message) return;

    input.value = "";

    addMessage(message, "user");
    setOrbState("thinking");

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || `HTTP ${response.status}`
            );
        }

        currentMode = "cloud";

        addMessage(data.message, "system");
        speak(data.message);

    } catch (error) {
        console.error("Davisn chat error:", error);

        addMessage(
            error.message || "Davisn could not reach the AI service.",
            "system"
        );

    } finally {
        setOrbState("ready");
    }
}


/* ============================================================
   CHAT EVENTS
============================================================ */

if (input) {
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
}

if ($("sendButton")) {
    $("sendButton").addEventListener("click", sendMessage);
}

if (orb) {
    orb.addEventListener("click", sendMessage);
}


/* ============================================================
   WEB MODE
============================================================ */

function updateModeUI() {
    const local = $("localMode");
    const cloud = $("cloudMode");

    if (local) {
        local.classList.remove("active");
        local.disabled = true;
        local.title = "Local AI is not available in the web version yet.";
    }

    if (cloud) {
        cloud.classList.add("active");
    }

    if ($("assistantMode")) {
        $("assistantMode").textContent = "CLOUD AI";
    }

    if ($("modeStatus")) {
        $("modeStatus").textContent = "CLOUD // GEMINI ENGINE";
    }
}

if ($("cloudMode")) {
    $("cloudMode").addEventListener("click", () => {
        addMessage("Davisn is already running in cloud mode.", "system");
    });
}


/* ============================================================
   CLOCK
============================================================ */

function updateClock() {
    const clock = $("clock");

    if (!clock) return;

    clock.textContent = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
}

updateClock();
setInterval(updateClock, 1000);


/* ============================================================
   VOICE RECOGNITION
============================================================ */

const SpeechRecognitionAPI =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

if (SpeechRecognitionAPI) {
    recognition = new SpeechRecognitionAPI();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
        isListening = true;
        setOrbState("listening");
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;

        if (input) {
            input.value = transcript;
        }

        sendMessage();
    };

    recognition.onerror = (event) => {
        addMessage("Voice error: " + event.error, "system");
    };

    recognition.onend = () => {
        isListening = false;
        setOrbState("ready");
    };
}

function toggleVoice() {
    if (!recognition) {
        addMessage(
            "Voice recognition is not supported in this browser.",
            "system"
        );
        return;
    }

    if (isListening) {
        recognition.stop();
        return;
    }

    try {
        recognition.start();
    } catch (error) {
        console.warn(error);
    }
}

if ($("voiceButton")) {
    $("voiceButton").addEventListener("click", toggleVoice);
}


/* ============================================================
   CAMERA
============================================================ */

async function openCamera() {
    const panel = $("cameraPanel");
    const video = $("cameraVideo");

    if (!panel || !video) return;

    if (!navigator.mediaDevices?.getUserMedia) {
        addMessage("Camera access is unavailable in this browser.", "system");
        return;
    }

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user" },
            audio: false
        });

        video.srcObject = cameraStream;
        panel.classList.add("active");

        if ($("faceStatus")) {
            $("faceStatus").textContent = "CAMERA ACTIVE";
        }

        startFacePresenceDetection();

    } catch (error) {
        console.error(error);
        addMessage("Camera access was denied or unavailable.", "system");
    }
}

function closeCamera() {
    if (faceDetectionTimer) {
        clearInterval(faceDetectionTimer);
        faceDetectionTimer = null;
    }

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    if ($("cameraVideo")) {
        $("cameraVideo").srcObject = null;
    }

    if ($("cameraPanel")) {
        $("cameraPanel").classList.remove("active");
    }

    if ($("faceStatus")) {
        $("faceStatus").textContent = "CAMERA OFFLINE";
    }
}

if ($("cameraButton")) {
    $("cameraButton").addEventListener("click", openCamera);
}

if ($("cameraClose")) {
    $("cameraClose").addEventListener("click", closeCamera);
}


/* ============================================================
   FACE PRESENCE
============================================================ */

function startFacePresenceDetection() {
    const video = $("cameraVideo");

    if (!video || !("FaceDetector" in window)) {
        if ($("faceStatus")) {
            $("faceStatus").textContent =
                "CAMERA ACTIVE // FACE DETECTION UNAVAILABLE";
        }
        return;
    }

    const detector = new FaceDetector({
        fastMode: true,
        maxDetectedFaces: 5
    });

    async function scan() {
        if (!cameraStream || video.readyState < 2) return;

        try {
            const faces = await detector.detect(video);

            if ($("faceStatus")) {
                $("faceStatus").textContent = faces.length
                    ? "FACE DETECTED"
                    : "SCANNING";
            }
        } catch (error) {
            console.warn("Face detection:", error);
        }
    }

    scan();
    faceDetectionTimer = setInterval(scan, 1000);
}


/* ============================================================
   WEB BLUETOOTH STATUS
============================================================ */

function setBluetoothStatus(text) {
    if ($("bluetoothStatus")) {
        $("bluetoothStatus").textContent = text;
    }
}

function setBluetoothCount(count) {
    if ($("bluetoothCount")) {
        $("bluetoothCount").textContent = String(count);
    }
}

function scanBluetooth() {
    setBluetoothStatus("BLUETOOTH SCANNING UNAVAILABLE IN WEB MVP");
    setBluetoothCount(0);

    addMessage(
        "Bluetooth radar is temporarily disabled in Davisn Web.",
        "system"
    );
}

if ($("bluetoothScan")) {
    $("bluetoothScan").addEventListener("click", scanBluetooth);
}


/* ============================================================
   SYSTEM STATUS
============================================================ */

async function checkBackend() {
    try {
        const response = await fetch(`${API_BASE}/api/health`, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Backend unavailable");
        }

        const data = await response.json();

        if (data.success) {
            if ($("systemStatus")) {
                $("systemStatus").textContent = "SYSTEM ONLINE";
            }

            if ($("statusDot")) {
                $("statusDot").style.background = "#00eaff";
            }

            setOrbState("ready");
        }

    } catch (error) {
        console.error("Backend status:", error);

        if ($("systemStatus")) {
            $("systemStatus").textContent = "BACKEND OFFLINE";
        }
    }
}


/* ============================================================
   MEMORY STATUS
============================================================ */

async function checkMemory() {
    try {
        const response = await fetch(`${API_BASE}/api/memory`);
        const data = await response.json();

        if (data.success) {
            console.log("Davisn memory:", data);
        }
    } catch (error) {
        console.warn("Memory status unavailable:", error);
    }
}


/* ============================================================
   CLEAR CONSOLE
============================================================ */

if ($("clearButton")) {
    $("clearButton").addEventListener("click", () => {
        if (messages) {
            messages.innerHTML = "";
        }

        addMessage("Console cleared.", "system");
    });
}


/* ============================================================
   INITIALIZATION
============================================================ */

async function initialize() {
    setOrbState("ready");

    updateModeUI();

    await checkBackend();
    await checkMemory();
}

initialize();


/* ============================================================
   CLEANUP
============================================================ */

window.addEventListener("beforeunload", () => {
    closeCamera();

    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
});
