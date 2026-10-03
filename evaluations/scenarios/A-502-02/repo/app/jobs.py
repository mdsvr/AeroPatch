"""A file-backed job queue: one file per job in a spool directory."""

import json
import os
import pickle
import uuid

JOB_SUFFIX = ".job"
PICKLE_MAGIC = b"\x80"
REQUIRED_FIELDS = ("name", "args", "priority")
MAX_PRIORITY = 9


class JobError(ValueError):
    """Raised for job files that cannot be read or do not describe a job."""


def _validated(job):
    """Return `job` if it is a well-formed job description, else raise JobError."""
    if not isinstance(job, dict):
        raise JobError("a job must be an object")
    missing = [field for field in REQUIRED_FIELDS if field not in job]
    if missing:
        raise JobError(f"job is missing {', '.join(missing)}")
    if not isinstance(job["name"], str) or not isinstance(job["args"], list):
        raise JobError("job name must be text and args a list")
    if not isinstance(job["priority"], int) or not 0 <= job["priority"] <= MAX_PRIORITY:
        raise JobError(f"priority must be an integer from 0 to {MAX_PRIORITY}")
    return job


def save_job(spool_dir, job):
    """Write a job into the spool directory and return the path of its file."""
    job = _validated(job)
    os.makedirs(spool_dir, exist_ok=True)
    path = os.path.join(spool_dir, uuid.uuid4().hex + JOB_SUFFIX)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job, f)
    return path


def load_job(path):
    """Read one job file from the spool directory.

    Other hosts drop job files into the spool over the upload endpoint. Files written by
    workers older than v2 are pickles; newer ones are JSON.
    """
    with open(path, "rb") as f:
        raw = f.read()
    try:
        if raw.startswith(PICKLE_MAGIC):
            job = pickle.loads(raw)
        else:
            job = json.loads(raw.decode("utf-8"))
    except (pickle.UnpicklingError, EOFError, ValueError) as exc:
        raise JobError(f"unreadable job file: {os.path.basename(path)}") from exc
    return _validated(job)


def job_files(spool_dir):
    """Paths of the job files in the spool directory, sorted by file name."""
    if not os.path.isdir(spool_dir):
        return []
    return sorted(
        os.path.join(spool_dir, name) for name in os.listdir(spool_dir) if name.endswith(JOB_SUFFIX)
    )


def pending(spool_dir):
    """The readable jobs in the spool, most urgent first (priority 0 is the most urgent).

    Files that are not valid jobs are skipped; `rejected` lists them.
    """
    jobs = []
    for path in job_files(spool_dir):
        try:
            jobs.append(load_job(path))
        except JobError:
            continue
    return sorted(jobs, key=lambda job: (job["priority"], job["name"]))


def rejected(spool_dir):
    """File names of the spool entries that are not valid jobs."""
    bad = []
    for path in job_files(spool_dir):
        try:
            load_job(path)
        except JobError:
            bad.append(os.path.basename(path))
    return bad
