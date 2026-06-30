# MANIFEST: {"name": "cor_plot", "description": "Correlation matrix plot for multiple pollutants. Pass 2 or more series.", "input_type": "series", "output_type": "image", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_series_df(payload, localize_dates = FALSE)
if (length(built$pollutants) < 2) stop("cor_plot requires at least 2 series")
df <- built$df
cols <- built$pollutants
payload <- built$payload
plot_title <- openair_plot_title(payload)
summary_labs <- openair_summary_labels(payload)

use_dendrogram <- FALSE
if (requireNamespace("legendry", quietly = TRUE)) {
  if (utils::compareVersion(as.character(packageVersion("legendry")), "0.2.4") >= 0) {
    use_dendrogram <- TRUE
  }
}

outfile <- file.path(artifacts_dir, paste0("cor_plot_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 900, height = 900, res = 120)
openair::corPlot(
  df,
  pollutants = cols,
  dendrogram = use_dendrogram,
  cluster = TRUE,
  main = plot_title
)
invisible(grDevices::dev.off())

summary_note <- paste0("Correlation matrix for: ", paste(summary_labs, collapse = ", "))
if (!use_dendrogram) {
  summary_note <- paste0(summary_note, " [dendrogram omitted: install R package legendry>=0.2.4 on server]")
}

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = summary_note,
  tool = "cor_plot"
), auto_unbox = TRUE))
