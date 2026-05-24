import json
import time

from flask import Blueprint, request, jsonify

from ...ask.interactive import handle_question
from ...ask.session import create_session, destroy_session, get_session
from ...ask.transcribe import transcribe
from ...db.store import get_digest_by_date
from ...services.tts import generate_response_audio

bp = Blueprint("ask", __name__)


@bp.route("/session", methods=["POST"])
def session_create():
    data = request.get_json()
    if not data or not data.get("user_id") or not data.get("digest_date"):
        return jsonify({"error": "user_id and digest_date required"}), 400

    digest_text = get_digest_by_date(data["user_id"], data["digest_date"])
    if not digest_text:
        return jsonify({"error": "Digest not found"}), 404

    session_id = create_session(digest_text)
    return jsonify({"session_id": session_id})


@bp.route("/ask", methods=["POST"])
def ask():
    t_start = time.time()

    session_id = request.form.get("session_id", "")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    if get_session(session_id) is None:
        return jsonify({"error": "Session not found or expired"}), 404

    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "audio file required"}), 400

    audio_bytes = audio_file.read()
    filename = audio_file.filename or "audio.webm"

    t_stt = time.time()
    question = transcribe(audio_bytes, filename)
    stt_latency = round(time.time() - t_stt, 3)
    if not question:
        return jsonify({"error": "Could not transcribe audio"}), 400

    result = handle_question(session_id, question)

    t_tts = time.time()
    response_audio = generate_response_audio(result["answer"])
    tts_latency = round(time.time() - t_tts, 3)

    total_latency = round(time.time() - t_start, 3)

    print(f"[ASK_E2E] {json.dumps({'session_id': session_id, 'stt_latency_s': stt_latency, 'tts_latency_s': tts_latency, 'total_latency_s': total_latency})}")

    return jsonify({
        "audio": response_audio,
        "question": result["question"],
        "answer": result["answer"],
    })


@bp.route("/session/destroy", methods=["POST"])
def session_destroy():
    data = request.get_json(silent=True)
    if not data or not data.get("session_id"):
        return jsonify({"error": "session_id required"}), 400

    destroy_session(data["session_id"])
    return jsonify({"ok": True})
