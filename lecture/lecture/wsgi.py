#!/usr/bin/env python

import datetime
from enum import Enum

from flask import Flask, redirect, render_template, request, url_for


class YTPlayerState(Enum):
    UNSTARTED = -1
    ENDED = 0
    PLAYING = 1
    PAUSED = 2
    BUFFERING = 3
    CUED = 5


app = Flask(__name__)

flag = "flag{this_is_a_fake_flag}"
youtube_id = "AKTYVWCi6ss"
total_time = datetime.timedelta(minutes=13, seconds=39)
timeline = []


@app.route("/")
def index():
    return redirect(url_for("lecture", youtube_id=youtube_id))


@app.route("/<youtube_id>/")
def lecture(youtube_id):
    return render_template("lecture.html", youtube_id=youtube_id)


@app.route("/<youtube_id>/telemetry", methods=["GET", "POST"])
def update_telemetry(youtube_id):
    fields = {
        "reason": str,
        "player": ["state", "time", "muted", "volume", "rate", "loaded", "duration", "url"],
        "document": ["visibility", "fullscreen", "agent"],
    }
    for field in fields:
        if field not in request.json:
            return {"error": f"Missing required data"}, 400
        if isinstance(fields[field], list):
            for sub_field in fields[field]:
                if sub_field not in request.json[field]:
                    return {"error": f"Missing required data"}, 400
    event = request.json.copy()
    event["player"]["state"] = YTPlayerState(event["player"]["state"])
    event["youtube_id"] = youtube_id
    event["timestamp"] = datetime.datetime.now()
    timeline.append(event)

    result = {}

    valid_coverage, invalid_coverage = resolve_timeline_coverage(timeline)
    result["coverage"] = {"valid": valid_coverage, "invalid": invalid_coverage}

    completed = sum(end - start for start, end in valid_coverage) > total_time.total_seconds() - 5
    if completed:
        result["flag"] = flag

    return result


def resolve_timeline_coverage(timeline):
    if not timeline:
        return

    valid_coverage = []
    invalid_coverage = []

    last_time = timeline[0]["player"]["time"]
    last_timestamp = timeline[0]["timestamp"]

    for event in timeline[1:]:
        elapsed_time = event["player"]["time"] - last_time
        elapsed_timestamp = event["timestamp"] - last_timestamp

        if elapsed_timestamp.total_seconds() * 2 + 2 > elapsed_time > 0:
            valid_coverage.append((last_time, event["player"]["time"]))
        elif elapsed_time > 0:
            invalid_coverage.append((last_time, event["player"]["time"]))

        last_time = event["player"]["time"]
        last_timestamp = event["timestamp"]

    def merge_intervals(intervals):
        if not intervals:
            return []
        intervals = sorted(intervals, key=lambda x: x[0])
        merged = [intervals[0]]
        for current_start, current_end in intervals[1:]:
            last_start, last_end = merged[-1]
            if current_start <= last_end:
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                merged.append((current_start, current_end))
        return merged

    valid_coverage = merge_intervals(valid_coverage)
    invalid_coverage = merge_intervals(invalid_coverage)

    def subtract_intervals(intervals, subtracting):
        result = []
        for (int_start, int_end) in intervals:
            current_start = int_start
            for (sub_start, sub_end) in subtracting:
                if sub_end <= current_start or sub_start >= int_end:
                    continue
                if sub_start > current_start:
                    result.append((current_start, sub_start))
                current_start = max(current_start, sub_end)
                if current_start >= int_end:
                    break
            if current_start < int_end:
                result.append((current_start, int_end))
        return result

    invalid_coverage = subtract_intervals(invalid_coverage, valid_coverage)

    return valid_coverage, invalid_coverage

application = app
