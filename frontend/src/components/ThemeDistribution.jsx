export default function ThemeDistribution({ themeStats, integerFormat }) {
	if (!themeStats?.length) return null;

	return (
		<div className='themes-overview'>
			<h3>Visão Geral por Temas</h3>
			<div className='themes-list'>
				{themeStats.map((stat, idx) => {
					const posPct = Math.round((stat.positive / stat.total) * 100) || 0;
					const negPct = Math.round((stat.negative / stat.total) * 100) || 0;

					return (
						<div className='theme-row' key={`theme-stat-${idx}`}>
							<div className='theme-info'>
								<strong>{stat.theme.toUpperCase()}</strong>
								<span className='theme-mentions'>
									{integerFormat(stat.total)} menções totais
								</span>
							</div>

							<div className='review-bar-container'>
								<div
									className='review-bar positive'
									style={{ width: `${posPct}%` }}
									title={`${posPct}% Positivas`}
								/>
								<div
									className='review-bar negative'
									style={{ width: `${negPct}%` }}
									title={`${negPct}% Negativas`}
								/>
							</div>

							<div className='review-labels'>
								<span className='label-pos'>
									{" "}
									{integerFormat(stat.positive)} ({posPct}%)
								</span>
								<span className='label-neg'>
									{integerFormat(stat.negative)} ({negPct}%){" "}
								</span>
							</div>
						</div>
					);
				})}
			</div>
		</div>
	);
}
