import "../styles/search.css";

export default function SearchBox({ value, onChange }) {
	return (
		<div className='search-box'>
			<label>Buscar jogo</label>

			<input
				type='text'
				placeholder='Digite o nome de um jogo...'
				value={value}
				onChange={(e) => onChange(e.target.value)}
			/>

			<span className='hint'>Autocomplete visual em tempo real</span>
		</div>
	);
}
