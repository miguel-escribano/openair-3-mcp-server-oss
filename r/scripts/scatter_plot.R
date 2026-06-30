# MANIFEST: {"name": "scatter_plot", "description": "Flexible scatter plot between two pollutants. First series = x-axis, second = y-axis.", "input_type": "series", "output_type": "image", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_series_df(payload, localize_dates = FALSE)
if (length(built$pollutants) < 2) stop("scatter_plot requires at least 2 series (x and y)")
df <- built$df
cols <- built$pollutants
payload <- built$payload
plot_title <- openair_plot_title(payload)
summary_labs <- openair_summary_labels(payload)

outfile <- file.path(artifacts_dir, paste0("scatter_plot_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 900, height = 900, res = 120)
openair::scatterPlot(df, x = cols[1], y = cols[2], main = plot_title)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Scatter plot: ", summary_labs[1], " vs ", summary_labs[2]),
  tool = "scatter_plot"
), auto_unbox = TRUE))
