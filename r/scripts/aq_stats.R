# MANIFEST: {"name": "aq_stats", "description": "Calculate summary statistics for air pollution data: mean, median, percentiles, data capture %. Returns JSON.", "input_type": "series", "output_type": "stats", "timeout": 60}
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

result <- openair::aqStats(df, pollutant = pollutants)

cat(jsonlite::toJSON(list(
  stats = result,
  summary = paste0("AQ statistics for: ", paste(summary_labs, collapse = ", ")),
  tool = "aq_stats"
), auto_unbox = TRUE, na = "null"))
