# MANIFEST: {"name": "polar_freq", "description": "Polar frequency plot showing wind speed/direction frequencies and optional pollutant statistics.", "input_type": "wind_series", "output_type": "image", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_wind_df(payload)
df <- built$df
pollutants <- built$pollutants
payload <- built$payload
plot_title <- openair_plot_title(payload)
summary_labs <- openair_summary_labels(payload)
pollutant <- if (length(pollutants) > 0) pollutants[1] else NULL

outfile <- file.path(artifacts_dir, paste0("polar_freq_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 900, height = 900, res = 120)
if (!is.null(pollutant)) {
  openair::polarFreq(df, pollutant = pollutant, main = plot_title)
} else {
  openair::polarFreq(df)
}
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = if (!is.null(pollutant)) paste0("Polar frequency for ", summary_labs[1]) else "Polar frequency (wind only)",
  tool = "polar_freq"
), auto_unbox = TRUE))
