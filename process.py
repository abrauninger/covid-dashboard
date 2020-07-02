import pandas as pd
import plotly.graph_objs as go

from plotly.subplots import make_subplots


def run():
	df = pd.read_csv('covid-19-data/us-counties.csv')

	kc = df[(df['state'] == 'Washington') & (df['county'] == 'King')]
	kc = kc[['date', 'cases', 'deaths']]
	kc['new_cases'] = kc['cases'].diff().astype('Int64')
	kc['new_deaths'] = kc['deaths'].diff().astype('Int64')

	# Drop the first row with NaN diff values.
	kc = kc.drop(kc.index[0])

	kc['date'] = pd.to_datetime(kc['date'])

	kc['new_cases_moving_average_7_day'] = kc['new_cases'].rolling(7).mean()
	kc['new_deaths_moving_average_7_day'] = kc['new_deaths'].rolling(7).mean()

	kc_hosp = pd.read_excel('king-county-data-download/covid-data-daily-counts-june-30.xlsx', sheet_name='Hospitalizations')
	kc_hosp = kc_hosp[kc_hosp['Admission_Date'].notnull()]

	fig = make_subplots(
		rows=2, cols=1,
		shared_xaxes=True,
		vertical_spacing=0.1,
		subplot_titles=('New cases', 'Hospitalizations')
	)

	fig.add_trace(
		go.Bar(
			x=kc['date'],
			y=kc['new_cases'],
			name='New cases'
		),
		row=1, col=1
	)

	fig.add_trace(
		go.Scatter(
			x=kc['date'],
			y=kc['new_cases_moving_average_7_day'],
			name='7-day moving average'
		),
		row=1, col=1
	)

	fig.add_trace(
		go.Scatter(
			x=kc_hosp['Admission_Date'],
			y=kc_hosp['Hospitalizations'],
			name='Hospitalizations'
		),
		row=2, col=1
	)

	fig.update_layout(
		title_text='New cases in King County'
	)

	fig.write_html('output/output.html')

	return kc