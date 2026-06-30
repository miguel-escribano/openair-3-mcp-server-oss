# MANIFEST: {"name": "rolling_quantile", "description": "Calculate rolling quantile for a time series. Returns SeriesV1-compatible JSON.", "input_type": "series", "output_type": "series", "timeout": 60}
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

col <- pollutants[1]
width <- if (!is.null(payload$hours)) as.integer(payload$hours) else 8L
quantile_val <- if (!is.null(payload$quantile)) as.numeric(payload$quantile) else 0.95
series_name <- paste0(col, "_q", round(quantile_val * 100), "_", width, "h")

before_cols <- names(df)
result <- openair::rollingQuantile(
  df,
  pollutant = col,
  width = width,
  probs = quantile_val,
  align = "right"
)
new_cols <- setdiff(names(result), before_cols)
if (length(new_cols) == 0) stop("rollingQuantile produced no new columns")
src_col <- new_cols[1]
raw_vals <- unname(as.numeric(result[[src_col]]))
if (length(raw_vals) == 0 || all(is.na(raw_vals))) stop("rollingQuantile produced no values")

out <- list(
  timestamps = format(result$date, "%Y-%m-%dT%H:%M:%SZ"),
  series = list(list(name = series_name, unit = "", values = as.list(raw_vals))),
  summary = paste0(quantile_val * 100, "th percentile ", width, "h rolling for ", summary_labs[1]),
  tool = "rolling_quantile"
)
if (!is.null(meta_out)) out$meta <- meta_out

cat(jsonlite::toJSON(out, auto_unbox = TRUE, na = "null"))
