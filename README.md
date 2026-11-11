# Cambridge Market Intelligence

Daily dashboard backed by public FRED observations and Google News RSS headlines. GitHub Actions updates daily.json on scheduled weekday runs (20:30 UTC Sunday-Thursday = 07:30 Melbourne during daylight savings; 06:30 in winter).

## Deploy

1. Make the repository public (Settings > General > Danger Zone > Change repository visibility).
2. Settings > Pages > Deploy from branch > main > / (root).
3. Actions > Daily pre-market intelligence > Run workflow. Check it succeeds.
4. Open https://cambridgepw.github.io/Daily-update/ after Pages reports deployment.

This is an initial automated data-driven prototype. It does not automatically verify geopolitical claims, use a generative model, calculate historical correlations, or produce investment advice. Some sources may be delayed or unavailable. Always review dated source readings.
