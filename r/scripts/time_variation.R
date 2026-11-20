# MANIFEST: {"name": "time_variation", "description": "Temporal variation plots showing diurnal, day-of-week, and monthly patterns with uncertainty intervals. Multi-pollutant: auto-normalises when scales differ (openair normalise=TRUE).", "input_type": "series", "output_type": "image", "timeout": 90}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
suppressMessages(library(ggplot2))
suppressMessages(library(patchwork))
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

timestamps <- unlist(payload$timestamps)
series_list <- payload$series
if (is.null(timestamps) || length(timestamps) == 0) stop("timestamps required")
if (is.null(series_list) || length(series_list) == 0) stop("series required")

built <- openair_build_series_df(payload, localize_dates = FALSE)
df <- built$df
pollutants <- built$pollutants
name_pol <- pollutants
payload <- openair_payload_meta(payload)

use_normalise <- FALSE
if (length(pollutants) > 1) {
  ranges <- vapply(pollutants, function(p) {
    v <- df[[p]]
    v <- v[is.finite(v)]
    if (length(v) == 0) return(0)
    diff(range(v))
  }, numeric(1))
  pos <- ranges[ranges > 0]
  if (length(pos) >= 2 && (max(pos) / min(pos)) >= 10) {
    use_normalise <- TRUE
  }
}

local_tz <- NULL
if (!is.null(payload$meta) && !is.null(payload$meta$timezone)) {
  local_tz <- as.character(payload$meta$timezone)
}

outfile <- file.path(artifacts_dir, paste0("time_variation_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

plot_title <- openair_plot_title(payload)

# Short y-axis label: openair defaults to concatenating every pollutant column
# name, which for two device-named series overflows and collides across the
# faceted panels. Use the shared unit when all series agree, else a neutral
# label.
units <- unique(Filter(nzchar, vapply(series_list, function(s) {
  if (!is.null(s$unit)) as.character(s$unit) else ""
}, character(1))))
ylab_text <- if (length(units) == 1) units[[1]] else "value"

d_valid <- df$date[!is.na(df$date)]
span_days <- if (length(d_valid) >= 2) {
  as.numeric(difftime(max(d_valid), min(d_valid), units = "days"))
} else {
  0
}
show_month_panel <- span_days >= 60

tv_args <- list(
  df,
  pollutant = pollutants,
  normalise = use_normalise,
  name.pol = name_pol,
  local.tz = local_tz,
  conf.int = 0.95,
  ylab = ylab_text
)
tv_call <- function(..., plot) {
  do.call(openair_plot_call, c(list(openair::timeVariation), tv_args, list(...), list(plot = plot)))
}
hide_legend <- function(p) p + ggplot2::theme(legend.position = "none")
compose_tv_panels <- function(obj, include_month = TRUE) {
  top <- obj$plot[["hour.weekday"]] +
    ggplot2::guides(fill = "none") +
    ggplot2::theme(legend.position = "top", legend.title = ggplot2::element_blank())
  row <- hide_legend(obj$plot[["hour"]]) | hide_legend(obj$plot[["weekday"]])
  if (isTRUE(include_month)) {
    row <- hide_legend(obj$plot[["hour"]]) |
      hide_legend(obj$plot[["month"]]) |
      hide_legend(obj$plot[["weekday"]])
  }
  top / row +
    patchwork::plot_annotation(
      title = plot_title,
      caption = "mean and 95% confidence interval in mean"
    )
}

png_h <- if (show_month_panel) 900 else 750
grDevices::png(outfile, width = 1400, height = png_h, res = 120)
if (length(pollutants) > 1) {
  # Multi-series: openair (ggplot2 backend, v3.1.0) emits one colour legend per
  # sub-panel, so patchwork shows the key 2x (4 entries for 2 series). Build the
  # panels with plot=FALSE, then compose manually keeping the legend on the top
  # weekday row only. conf.int=0.95 is fixed, so the caption is constant.
  obj <- tv_call(plot = FALSE)
  print(compose_tv_panels(obj, include_month = show_month_panel))
} else if (show_month_panel) {
  # Single series: direct render when monthly panel is meaningful.
  tv_call(key = FALSE, main = plot_title, plot = TRUE)
} else {
  obj <- tv_call(plot = FALSE)
  print(compose_tv_panels(obj, include_month = FALSE))
}
invisible(grDevices::dev.off())

period_bits <- if (show_month_panel) "diurnal/weekly/monthly" else "diurnal/weekly (month omitted; span < 60 days)"
summary_note <- paste0("Time variation (", period_bits, ") for: ", paste(openair_summary_labels(payload), collapse = ", "))
if (use_normalise) {
  summary_note <- paste0(summary_note, " [normalised by mean — compare diurnal shape, not absolute units]")
}

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = summary_note,
  tool = "time_variation",
  normalise = use_normalise
), auto_unbox = TRUE))
