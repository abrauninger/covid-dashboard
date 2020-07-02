import pandas as pd
import plotly.graph_objs as go

from plotly.subplots import make_subplots


kc_xlsx_file = 'king-county-data-download/covid-data-daily-counts-june-30.xlsx'


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

	kc_hosp = pd.read_excel(kc_xlsx_file, sheet_name='Hospitalizations')
	kc_hosp = kc_hosp[kc_hosp['Admission_Date'].notnull()]
	kc_hosp['Moving_Average_7_Day'] = kc_hosp['Hospitalizations'].rolling(7).mean()

	kc_test = pd.read_excel(kc_xlsx_file, sheet_name='Tests')
	kc_test = kc_test[kc_test['Result_Date'].notnull()]
	kc_test['Moving_Average_7_Day'] = kc_test['Tests'].rolling(7).mean()

	joined = kc.join(kc_test.set_index('Result_Date'), on='date')
	joined['tests_per_case'] = joined['Tests'] / joined['new_cases']
	joined['tests_per_case_moving_average_7_day'] = joined['tests_per_case'].rolling(7).mean()

	fig = make_subplots(
		rows=4, cols=1,
		shared_xaxes=True,
		vertical_spacing=0.1,
		subplot_titles=('New cases', 'Hospitalizations', 'Tests', 'Tests per confirmed case')
	)

	fig.add_trace(
		go.Bar(
			x=kc['date'],
			y=kc['new_cases']
		),
		row=1, col=1
	)
	fig.add_trace(
		go.Scatter(
			x=kc['date'],
			y=kc['new_cases_moving_average_7_day']
		),
		row=1, col=1
	)

	fig.add_trace(
		go.Bar(
			x=kc_hosp['Admission_Date'],
			y=kc_hosp['Hospitalizations']
		),
		row=2, col=1
	)
	fig.add_trace(
		go.Scatter(
			x=kc_hosp['Admission_Date'],
			y=kc_hosp['Moving_Average_7_Day']
		),
		row=2, col=1
	)

	fig.add_trace(
		go.Bar(
			x=kc_test['Result_Date'],
			y=kc_test['Tests']
		),
		row=3, col=1
	)
	fig.add_trace(
		go.Scatter(
			x=kc_test['Result_Date'],
			y=kc_test['Moving_Average_7_Day']
		),
		row=3, col=1
	)

	fig.add_trace(
		go.Bar(
			x=joined['date'],
			y=joined['tests_per_case']
		),
		row=4, col=1
	)
	fig.add_trace(
		go.Scatter(
			x=joined['date'],
			y=joined['tests_per_case_moving_average_7_day']
		),
		row=4, col=1
	)

	fig.update_layout(
		title_text='COVID-19 metrics in King County, WA',
		showlegend=False
	)

	fig.write_html('output/output.html')

	return kc