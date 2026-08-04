# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.

## Testing

Component tests run on Vitest + jsdom + Testing Library:

```bash
npm test          # run the suite once
npm run typecheck # tsc -b (project references)
npm run build     # typecheck + production build
```

- Test setup lives in `src/test/setup.ts` (auto `cleanup()` after each test).
- Vitest is configured via `vite.config.ts` (`test.environment: 'jsdom'`).
- New component tests go in `src/components/__tests__/`.

## Profile Health dashboard

The Home page renders server-driven profile analysis from two endpoints
(`ProfileService.getQualityReport` / `getImprovementQueue`):

- `HealthScore` + `DimensionBreakdown` show the aggregate health score and per-dimension bars.
- `ImprovementQueue` groups `UnifiedRecommendation` items by rule and supports
  priority / resolution-type filtering (server-side via query params).
- `RecommendationCard` renders the priority + resolution badges and an expandable
  details panel (reason, suggested action, evidence refs).

