import { RouteLoading } from "./migration/loading";
import { AppLayout } from "./neighborfood/AppLayout";
import { HomePage } from "./neighborfood/HomePage";
import { useRoute } from "./migration/core";
import { Guard, Screen } from "./migration/routes";
import "./neighborfood/home.css";
import "./migration/design.css";
export default function App() {
  const { page, q } = useRoute();
  return (
    <AppLayout page={page}>
      <RouteLoading key={page + q.toString()}>
        <Guard page={page}>
          {page === "Home" ? (
            <HomePage />
          ) : (
            <Screen key={page + q.toString()} page={page} q={q} />
          )}
        </Guard>
      </RouteLoading>
    </AppLayout>
  );
}
