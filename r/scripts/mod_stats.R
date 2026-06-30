# MANIFEST: {"name": "mod_stats", "description": "Model evaluation statistics (FAC2, MB, RMSE, r, …). Pass two series: first = model/predicted, second = observed.", "input_type": "series", "output_type": "stats", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

built <- openair_build_series_df(payload, localize_dates = FALSE)
if (length(built$pollutants) < 2) {
  stop("mod_stats requires at least 2 series: first = model/predicted, second = observed")
}
df <- built$df
cols <- built$pollutants
payload <- built$payload
summary_labs <- openair_summary_labels(payload)

mod_col <- cols[1]
obs_col <- cols[2]
openair_req_cols(df, c(mod_col, obs_col))

result <- openair::modStats(df, mod = mod_col, obs = obs_col)
if (is.data.frame(result)) {
  stats <- jsonlite::fromJSON(jsonlite::toJSON(result, dataframe = "rows"), simplifyVector = TRUE)
} else {
  stats <- list(output = as.character(result))
}

cat(jsonlite::toJSON(list(
  stats = stats,
  summary = paste0("Model stats: ", summary_labs[1], " vs ", summary_labs[2]),
  tool = "mod_stats",
  mod = mod_col,
  obs = obs_col
), auto_unbox = TRUE, na = "null"))
