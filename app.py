"""
Flask web application for generating marketing campaign directions,
storyboards, and placeholder images based on a client's brief.  After
logging in with a simple username and password, users can enter their
project brief (product description, the number of videos they need,
and the desired length of each video).  The application then
generates three different campaign directions (safe, innovative,
experimental), storyboards for each direction, and displays images
representative of those directions.  Optionally, the code includes
a helper function to call the MiniMax Hailuo 02 API via Novita or
another provider.  You will need a valid API key to enable that
functionality; by default it is disabled because network calls are
blocked in this environment.

This application is intentionally simple and uses in‑memory user
credentials.  Do not use it in production without adding proper
authentication, rate limiting, CSRF protection, and secure secret
management.
"""

import os
import time
from typing import Dict, List

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)
import requests


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

app = Flask(__name__)

# Change this secret key in production.  It is used to secure session
# cookies.  Here we read it from an environment variable if available.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me")

# Hard-coded user credentials.  In a real system you should store
# usernames and hashed passwords in a secure database.  For this demo
# application we just use a dictionary.
USERS: Dict[str, str] = {
    "demo": "password123",
    "admin": "admin",
}

# Optionally provide your Hailuo API key via environment variable.
HAILUO_API_KEY = os.environ.get("HAILUO_API_KEY")


# ----------------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------------

def generate_directions(product: str) -> Dict[str, str]:
    """
    Generate three high‑level marketing directions based on the product
    description.  These directions are meant to inspire the next
    creative steps and can be modified to suit different clients.  The
    returned dictionary contains three keys: 'safe', 'innovative', and
    'experimental'.

    Parameters
    ----------
    product : str
        The client's product description.

    Returns
    -------
    Dict[str, str]
        A mapping from direction name to descriptive text.
    """
    # In a real system you might call an LLM or use a template engine.
    # Here we craft some example directions using simple heuristics.
    safe = (
        f"Focus on the core benefits of {product} and highlight its reliability "
        "and ease of use.  Use straightforward visuals, clear messaging, and a "
        "friendly tone that reinforces trust."
    )
    innovative = (
        f"Emphasise how {product} pushes boundaries by showcasing its unique "
        "features or cutting‑edge technology.  Incorporate dynamic camera "
        "movements, modern graphic overlays, and a forward‑thinking narrative."
    )
    experimental = (
        f"Take a bold, artistic approach to expressing the essence of {product}.  "
        "Use abstract storytelling, unexpected metaphors, or surreal visuals "
        "that evoke emotion and curiosity."
    )
    return {
        "safe": safe,
        "innovative": innovative,
        "experimental": experimental,
    }


def generate_storyboards(product: str, num_videos: int, duration: int) -> Dict[str, List[Dict[str, str]]]:
    """
    Build simple storyboards for each campaign direction.  Each storyboard
    consists of several scenes with a description and an AI prompt for
    generating a video using Hailuo 02.  The number of scenes is fixed
    at three for simplicity but can be adjusted.  The total number of
    storyboards created matches the number of directions (three).

    Parameters
    ----------
    product : str
        Description of the client's product.
    num_videos : int
        The number of videos requested by the client.  We use this to
        annotate our storyboards but do not dynamically create multiple
        separate storyboards for each requested video.  You could
        extend this to generate distinct storyboards per video.
    duration : int
        Duration of each video in seconds.  This value informs the
        narrative pacing in the scene descriptions.

    Returns
    -------
    Dict[str, List[Dict[str, str]]]
        A mapping from direction name to a list of scenes.  Each scene is
        represented by a dictionary with 'description' and 'prompt' keys.
    """
    # Determine approximate scene length based on duration.  We'll divide
    # the video into three equal parts.
    segment_length = max(1, duration // 3)

    def build_scenes(adjective: str) -> List[Dict[str, str]]:
        return [
            {
                "description": (
                    f"Scene 1 ({segment_length}s): Introduce {product} in a {adjective} way, "
                    "highlighting its main value proposition."
                ),
                "prompt": (
                    f"An opening shot that showcases {product} with {adjective} tone; "
                    "smooth camera movement and soft lighting."
                ),
            },
            {
                "description": (
                    f"Scene 2 ({segment_length}s): Expand on how {product} benefits the target "
                    f"audience, incorporating a {adjective} visual metaphor."
                ),
                "prompt": (
                    f"A middle shot using a {adjective} metaphor to illustrate {product}'s "
                    "advantage; dynamic transitions and engaging colours."
                ),
            },
            {
                "description": (
                    f"Scene 3 ({segment_length}s): Conclude by motivating viewers to act, "
                    "leaving them with a memorable {adjective} impression of {product}."
                ),
                "prompt": (
                    f"A closing shot that leaves a strong {adjective} impression of {product}; "
                    "dramatic composition and inspiring text overlay."
                ),
            },
        ]

    return {
        "safe": build_scenes("safe and trustworthy"),
        "innovative": build_scenes("innovative and modern"),
        "experimental": build_scenes("experimental and artistic"),
    }


def call_hailuo_api(prompt: str, duration: int, image: str = None, end_image: str = None, resolution: str = "768P") -> Dict[str, str]:
    """
    Submit a text‑to‑video request to the Hailuo 02 API via Novita
    (https://api.novita.ai/v3/async/minimax-hailuo-02) and poll for the
    result.  This function returns the video URL when the task is
    complete.  Network requests are disabled in this environment, so the
    body of this function is illustrative only.  Uncomment and adjust
    the code to call the actual API when deploying.

    Parameters
    ----------
    prompt : str
        The text prompt describing the desired video.
    duration : int
        Length of the video in seconds.  Supported values for Hailuo are 6 and 10.
    image : str, optional
        Optional URL or base64 string of the initial frame.  Defaults to None.
    end_image : str, optional
        Optional URL or base64 string of the ending frame.  Defaults to None.
    resolution : str, optional
        Desired output resolution ('768P' or '1080P').  Defaults to '768P'.

    Returns
    -------
    Dict[str, str]
        A dictionary containing the task ID and the video URL (if available).
    """
    # Check that the API key is present
    if not HAILUO_API_KEY:
        # When no API key is provided, return a placeholder response.
        return {
            "task_id": None,
            "video_url": None,
            "message": "Hailuo API key not configured; skipping real API call."
        }

    # The following code is commented out to prevent network calls during demo.
    # Uncomment it when running in an environment with network access.
    """
    headers = {
        "Authorization": f"Bearer {HAILUO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "enable_prompt_expansion": True,
    }
    if image:
        payload["image"] = image
    if end_image:
        payload["end_image"] = end_image

    # Submit the asynchronous request
    response = requests.post(
        "https://api.novita.ai/v3/async/minimax-hailuo-02",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    task_id = response.json().get("task_id")
    if not task_id:
        raise RuntimeError("Failed to get task_id from Hailuo API response")

    # Poll for the result.  In a real application you might want to use
    # asynchronous callbacks or webhooks instead of blocking polling.
    for _ in range(60):  # up to 60 attempts (~60 seconds)
        result_resp = requests.get(
            f"https://api.novita.ai/v3/async/task-result?task_id={task_id}",
            headers=headers,
            timeout=30,
        )
        result_resp.raise_for_status()
        data = result_resp.json()
        status = data.get("task", {}).get("status")
        if status == "TASK_STATUS_SUCCEED":
            videos = data.get("videos", [])
            video_url = videos[0].get("video_url") if videos else None
            return {"task_id": task_id, "video_url": video_url}
        elif status == "TASK_STATUS_FAILED":
            return {"task_id": task_id, "video_url": None, "message": "Generation failed"}
        # Otherwise wait and try again
        time.sleep(1)
    # Timed out
    return {"task_id": task_id, "video_url": None, "message": "Timed out waiting for video"}
    """

    # Fallback return when network calls are disabled
    return {
        "task_id": None,
        "video_url": None,
        "message": "Networking disabled; returning placeholder response."
    }


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def login() -> str:
    """
    Display the login page and handle login submissions.  On successful
    login, redirect the user to the dashboard.
    """
    if session.get("username"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username] == password:
            session["username"] = username
            return redirect(url_for("dashboard"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard() -> str:
    """
    Display the brief input form and handle submissions.  When the user
    submits their brief, generate directions and storyboards and
    render the results page.
    """
    if not session.get("username"):
        return redirect(url_for("login"))
    if request.method == "POST":
        product = request.form.get("product", "").strip()
        try:
            num_videos = int(request.form.get("num_videos", "1"))
        except ValueError:
            num_videos = 1
        try:
            duration = int(request.form.get("duration", "6"))
        except ValueError:
            duration = 6
        # Clamp values to reasonable ranges
        num_videos = max(1, min(num_videos, 10))
        duration = max(2, min(duration, 30))

        directions = generate_directions(product)
        storyboards = generate_storyboards(product, num_videos, duration)

        return render_template(
            "results.html",
            product=product,
            num_videos=num_videos,
            duration=duration,
            directions=directions,
            storyboards=storyboards,
        )
    return render_template("index.html")


@app.route("/logout")
def logout() -> str:
    """
    Log the user out by clearing the session and redirect to the login
    page.
    """
    session.pop("username", None)
    return redirect(url_for("login"))


# Example API endpoint to generate a video.  This endpoint is not called
# directly by the pages in this demo but demonstrates how you could
# integrate the Hailuo API asynchronously.
@app.route("/api/generate_video", methods=["POST"])
def api_generate_video():
    if not session.get("username"):
        return jsonify({"error": "unauthenticated"}), 401
    data = request.get_json(force=True)
    prompt = data.get("prompt")
    duration = int(data.get("duration", 6))
    # Normally call the Hailuo API here
    result = call_hailuo_api(prompt, duration)
    return jsonify(result)


if __name__ == "__main__":
    # When running from the command line, start the development server.
    # The host is set to '0.0.0.0' so the app is accessible from within
    # a container, and debug mode is disabled by default.
    app.run(host="0.0.0.0", port=5000, debug=False)