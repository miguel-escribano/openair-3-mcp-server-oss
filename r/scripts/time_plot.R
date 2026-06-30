# MANIFEST: {"name": "time_plot", "description": "Plot one or more pollutant time series. Indoor or outdoor data. Requires date + at least one pollutant column.", "input_type": "series", "output_type": "image", "timeout": 60}
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
plot_title <- openair_plot_title(payload)
summary_labs <- openair_summary_labels(payload)

outfile <- file.path(artifacts_dir, paste0("time_plot_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 600, res = 120)
if (length(pollutants) > 1) {
  openair::timePlot(df, pollutant = pollutants, main = plot_title, name.pol = pollutants)
} else {
  openair::timePlot(df, pollutant = pollutants, main = plot_title)
}
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Time series: ", paste(summary_labs, collapse = ", ")),
  tool = "time_plot"
), auto_unbox = TRUE))
