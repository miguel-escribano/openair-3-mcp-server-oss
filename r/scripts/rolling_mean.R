# MANIFEST: {"name": "rolling_mean", "description": "Calculate rolling mean for a time series. Returns SeriesV1-compatible JSON with smoothed values.", "input_type": "series", "output_type": "series", "timeout": 60}
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

poll <- pollutants[1]
width <- if (!is.null(payload$hours)) as.integer(payload$hours) else 8L
col_out <- paste0(poll, "_rolling_", width, "h")

result <- openair::rollingMean(
  df,
  pollutant = poll,
  width = width,
  new.name = col_out,
  align = "right"
)
raw_vals <- unname(as.numeric(result[[col_out]]))
if (length(raw_vals) == 0 || all(is.na(raw_vals))) {
  stop(paste0("rollingMean produced no values for ", col_out))
}

out <- list(
  timestamps = format(result$date, "%Y-%m-%dT%H:%M:%SZ"),
  series = list(list(name = col_out, unit = "", values = as.list(raw_vals))),
  summary = paste0(width, "-hour rolling mean for ", summary_labs[1]),
  tool = "rolling_mean"
)
if (!is.null(meta_out)) out$meta <- meta_out

cat(jsonlite::toJSON(out, auto_unbox = TRUE, na = "null"))
