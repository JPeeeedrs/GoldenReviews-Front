import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import SteamSpyTopGames from "../topics_analizers/games_analizer/games_anlyses.jsx";

createRoot(document.getElementById("root")).render(
	<StrictMode>
		<SteamSpyTopGames />
	</StrictMode>,
);
