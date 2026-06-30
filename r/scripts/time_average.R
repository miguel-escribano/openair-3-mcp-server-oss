# MANIFEST: {"name": "time_average", "description": "Resample a time series to a different time resolution (e.g. hourly to daily means). Returns SeriesV1-compatible JSON.", "input_type": "series", "output_type": "series", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

built <- openair_build_series_df(payload, localize_dates = FALSE)
df <- built$df
pollutants <- built$pollutants
summary_labs <- openair_summary_labels(payload)
meta_out <- openair_meta_out(payload)

avg_time <- if (!is.null(payload$avg_time)) payload$avg_time else "day"

result <- openair::timeAverage(df, avg.time = avg_time)

timestamps_out <- format(result$date, "%Y-%m-%dT%H:%M:%SZ")
series_out <- lapply(pollutants, function(col) {
  list(name = col, unit = "", values = as.list(result[[col]]))
})

out <- list(
  timestamps = timestamps_out,
  series = series_out,
  summary = paste0("Time averaged (", avg_time, ") for: ", paste(summary_labs, collapse = ", ")),
  tool = "time_average"
)
if (!is.null(meta_out)) out$meta <- meta_out

cat(jsonlite::toJSON(out, auto_unbox = TRUE, na = "null"))
