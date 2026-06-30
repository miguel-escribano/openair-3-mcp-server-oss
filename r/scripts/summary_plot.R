# MANIFEST: {"name": "summary_plot", "description": "Multi-panel summary: time-series averages plus data completeness bars. Useful as a first look at coverage and levels.", "input_type": "series", "output_type": "image", "timeout": 90}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
lib_dir <- Sys.getenv("OPENAIR_R_LIB", unset = "r/common")
source(file.path(lib_dir, "series_df.R"))
source(file.path(lib_dir, "summary_fallback.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_series_df(payload)
df <- built$df
pollutants <- built$pollutants
payload <- built$payload
summary_labs <- openair_summary_labels(payload)

valid_pc <- pollutants[sapply(pollutants, function(x) sum(!is.na(df[[x]])) > 0)]
if (length(valid_pc) == 0) stop("All pollutant columns are entirely NA.")
df_sub <- df[, c("date", valid_pc), drop = FALSE]

avg_time <- if (!is.null(payload$avg_time) && nzchar(as.character(payload$avg_time)[1])) {
  as.character(payload$avg_time)
} else {
  openair_infer_avg_time(df$date, default = "day")
}

outfile <- file.path(artifacts_dir, paste0("summary_plot_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 900, res = 120)
used_fallback <- FALSE
fn <- tryCatch(openair_resolve_fn("summaryPlot"), error = function(e) NULL)
if (is.null(fn)) {
  fn <- tryCatch(openair_resolve_fn("summaryData"), error = function(e) NULL)
}
if (!is.null(fn)) {
  err <- tryCatch({
    do.call(fn, list(mydata = df_sub, avg.time = avg_time))
    NULL
  }, error = function(e) e)
  if (!is.null(err)) {
    used_fallback <- TRUE
    openair_summary_plot_fallback(df_sub, valid_pc, avg_time)
  }
} else {
  used_fallback <- TRUE
  openair_summary_plot_fallback(df_sub, valid_pc, avg_time)
}
invisible(grDevices::dev.off())

mode_note <- if (isTRUE(used_fallback)) " (ggplot2 fallback)" else ""
cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0(
    "Summary plot (", avg_time, ") for: ",
    paste(summary_labs, collapse = ", "),
    mode_note
  ),
  tool = "summary_plot"
), auto_unbox = TRUE))
