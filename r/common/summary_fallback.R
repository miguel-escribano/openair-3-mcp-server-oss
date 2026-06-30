# ggplot2 fallback when openair::summaryPlot / summaryData is unavailable.

openair_summary_plot_fallback <- function(df, pollutants, avg_time = "day") {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("ggplot2 is required for the summary plot fallback.")
  }
  if (!requireNamespace("lubridate", quietly = TRUE)) {
    stop("lubridate is required for the summary plot fallback.")
  }
  pc <- pollutants[pollutants %in% names(df)]
  if (length(pc) == 0) stop("No pollutant columns found for summary plot.")

  .avg <- function(d, period) {
    floor_fn <- switch(
      period,
      min = function(x) lubridate::floor_date(x, "minute"),
      hour = function(x) lubridate::floor_date(x, "hour"),
      day = function(x) as.POSIXct(as.Date(x), tz = "UTC"),
      week = function(x) lubridate::floor_date(x, "week"),
      month = function(x) lubridate::floor_date(x, "month"),
      year = function(x) lubridate::floor_date(x, "year"),
      function(x) as.POSIXct(as.Date(x), tz = "UTC")
    )
    d$period_ <- floor_fn(d$date)
    dates <- sort(unique(d$period_))
    out <- data.frame(date = dates)
    for (v in pc) {
      out[[v]] <- as.numeric(
        tapply(d[[v]], d$period_, mean, na.rm = TRUE)[
          match(as.character(dates), names(tapply(d[[v]], d$period_, mean, na.rm = TRUE)))
        ]
      )
    }
    out
  }

  df_avg <- tryCatch(.avg(df, avg_time), error = function(e) df)

  if (requireNamespace("tidyr", quietly = TRUE)) {
    df_long <- tidyr::pivot_longer(
      df_avg,
      cols = pc,
      names_to = "variable",
      values_to = "value"
    )
  } else {
    rows <- lapply(pc, function(v) {
      data.frame(
        date = df_avg$date,
        variable = v,
        value = df_avg[[v]],
        stringsAsFactors = FALSE
      )
    })
    df_long <- do.call(rbind, rows)
  }
  df_long$variable <- factor(df_long$variable, levels = pc)

  n <- nrow(df)
  cdf <- data.frame(
    variable = factor(pc, levels = rev(pc)),
    pct = vapply(pc, function(v) round(sum(!is.na(df[[v]])) / n * 100), numeric(1)),
    stringsAsFactors = FALSE
  )
  cdf$fill_col <- ifelse(cdf$pct > 80, "#1d8348", ifelse(cdf$pct > 50, "#d4ac0d", "#922b21"))

  base_theme <- ggplot2::theme_bw(base_size = 11) +
    ggplot2::theme(
      strip.background = ggplot2::element_rect(fill = "#2471a3"),
      strip.text = ggplot2::element_text(colour = "white", face = "bold", size = 9),
      panel.grid.minor = ggplot2::element_blank(),
      plot.title = ggplot2::element_text(face = "bold", colour = "#154360", size = 12)
    )

  g_ts <- ggplot2::ggplot(df_long, ggplot2::aes(x = date, y = value, colour = variable)) +
    ggplot2::geom_line(linewidth = 0.45, na.rm = TRUE) +
    ggplot2::facet_wrap(~variable, scales = "free_y", ncol = 1) +
    ggplot2::scale_x_datetime(date_labels = "%b %Y") +
    ggplot2::scale_colour_brewer(palette = "Set1", guide = "none") +
    ggplot2::labs(
      title = paste0("Summary — ", avg_time, " averages"),
      x = NULL,
      y = "Value"
    ) +
    base_theme

  g_cmp <- ggplot2::ggplot(cdf, ggplot2::aes(x = variable, y = pct, fill = fill_col)) +
    ggplot2::geom_col(width = 0.6) +
    ggplot2::geom_text(
      ggplot2::aes(label = paste0(pct, "%")),
      hjust = -0.15,
      size = 3.2,
      fontface = "bold"
    ) +
    ggplot2::coord_flip(ylim = c(0, 115)) +
    ggplot2::scale_fill_identity() +
    ggplot2::labs(title = "Data Completeness", x = NULL, y = "% valid records") +
    base_theme +
    ggplot2::theme(panel.grid.major.y = ggplot2::element_blank())

  np <- length(pc)
  if (requireNamespace("gridExtra", quietly = TRUE)) {
    lmat <- rbind(
      matrix(1L, nrow = max(np * 2, 4), ncol = 1),
      matrix(2L, nrow = max(2, np), ncol = 1)
    )
    gridExtra::grid.arrange(g_ts, g_cmp, layout_matrix = lmat)
  } else {
    print(g_ts)
    print(g_cmp)
  }
  invisible(NULL)
}
