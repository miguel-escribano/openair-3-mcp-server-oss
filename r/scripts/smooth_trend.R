# MANIFEST: {"name": "smooth_trend", "description": "Non-parametric smooth trend using GAM. Shows long-term variability with confidence intervals.", "input_type": "series", "output_type": "image", "timeout": 90}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_series_df(payload)
df <- built$df
pollutants <- built$pollutants
payload <- built$payload
summary_labs <- openair_summary_labels(payload)

avg_time <- if (!is.null(payload$avg_time) && nzchar(as.character(payload$avg_time)[1])) {
  as.character(payload$avg_time)
} else {
  openair_infer_avg_time(df$date, default = "month")
}

outfile <- file.path(artifacts_dir, paste0("smooth_trend_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 600, res = 120)
openair::smoothTrend(
  df,
  pollutant = pollutants,
  avg.time = avg_time,
  main = openair_plot_title(payload)
)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Smooth trend (", avg_time, ") for: ", paste(summary_labs, collapse = ", ")),
  tool = "smooth_trend"
), auto_unbox = TRUE))
