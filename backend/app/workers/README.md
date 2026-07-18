# Workers

Background processing is orchestrated by `app.services.jobs.run_job_worker`,
which runs `VideoProcessingPipeline` in a worker thread.

Strategy plugins live under `app.processing.strategies`.
