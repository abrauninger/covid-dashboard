import pandas as pd
import plotly.graph_objs as go

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

	fig = go.Figure(
		data=[
			go.Bar(
				x=kc['date'],
				y=kc['new_cases']
			),
			go.Scatter(
				x=kc['date'],
				y=kc['new_cases_moving_average_7_day']
			),
			go.Scatter(
				x=kc_hosp['Admission_Date'],
				y=kc_hosp['Hospitalizations']
			)
		],
		layout=go.Layout(
			title='New cases in King County',
			xaxis_title='Date',
			yaxis_title='New Cases'
		)
	)

	fig.update_layout()

	fig.write_html('output/output.html')

	return kc