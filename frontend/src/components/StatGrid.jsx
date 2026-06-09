import "../styles/statgrid.css";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

const integerFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);

export default function StatGrid({ game, summary, metadata, meta }) {
	const owners = game?.owners ?? game?.steamspy?.owners;
	const totalSteamReviews =
		game?.total_reviews ?? game?.steamspy?.total_reviews ?? null;

	return (
		<div className='stat-grid'>
			<div className='stat-card'>
				<span>Reviews processadas</span>
				<strong>{integerFormat(summary?.reviews_analyzed ?? 0)}</strong>
			</div>
			<div className='stat-card good'>
				<span>Positivas</span>
				<strong>
					{integerFormat(summary?.positive_count ?? 0)} •{" "}
					{summary?.positive_percentage ?? 0}%
				</strong>
			</div>
			<div className='stat-card bad'>
				<span>Negativas</span>
				<strong>
					{integerFormat(summary?.negative_count ?? 0)} •{" "}
					{summary?.negative_percentage ?? 0}%
				</strong>
			</div>
			<div className='stat-card neutral'>
				<span>Idioma / limite</span>
				<strong>
					{meta?.language === "brazilian" ? "PT-BR" : meta?.language}
					&nbsp;•&nbsp;
					{integerFormat(meta?.maxReviewsRequested ?? 0)} máx.
				</strong>
			</div>
			{owners && (
				<div className='stat-card highlight'>
					<span>🧾 Estimativa de cópias (SteamSpy)</span>
					<strong>{owners}</strong>
				</div>
			)}
			{totalSteamReviews && (
				<div className='stat-card highlight'>
					<span>🗳️ Reviews totais na Steam</span>
					<strong>{integerFormat(totalSteamReviews)}</strong>
				</div>
			)}
			{metadata?.processing_time_seconds !== undefined && (
				<div className='stat-card neutral'>
					<span>Processamento IA</span>
					<strong>
						{metadata.processing_time_seconds}s &nbsp;•&nbsp;
						{metadata.model_version || "BERTopic"}
					</strong>
				</div>
			)}
		</div>
	);
}
