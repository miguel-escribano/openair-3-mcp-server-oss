# MANIFEST: {"name": "calc_percentile", "description": "Calculate percentile values from a time series. Returns percentile statistics as JSON.", "input_type": "series", "output_type": "stats", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

built <- openair_build_series_df(payload, localize_dates = FALSE)
df <- built$df
pollutants <- built$pollutants
payload <- built$payload
summary_labs <- openair_summary_labels(payload)

percentiles <- if (!is.null(payload$percentiles)) as.numeric(unlist(payload$percentiles)) else c(25, 50, 75, 95, 99)
avg_time <- if (!is.null(payload$avg_time)) payload$avg_time else "month"

result <- openair::calcPercentile(df, pollutant = pollutants[1], avg.time = avg_time, percentile = percentiles)

cat(jsonlite::toJSON(list(
  stats = result,
  summary = paste0("Percentiles (", paste(percentiles, collapse = "/"), ") for ", summary_labs[1], " by ", avg_time),
  tool = "calc_percentile"
), auto_unbox = TRUE, na = "null"))
