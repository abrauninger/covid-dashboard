import datetime
import mako.template
import pandas as pd
import plotly
import plotly.graph_objs as go

from plotly.subplots import make_subplots
from typing import NamedTuple


class Data(NamedTuple):
	cases_and_deaths: pd.DataFrame
	hospitalizations: pd.DataFrame
	tests: pd.DataFrame
	positive_test_rate: pd.DataFrame


def read_data():
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

	kc_xlsx_file = 'king-county-data-download/covid-data-daily-counts-2020-09-08.xlsx'

	# `read_excel` appears to have a bug that silently drops recent data from the xlsx file, for some reason
	# For now, work around this by reading from CSV instead
	#kc_hosp = pd.read_excel(kc_xlsx_file, sheet_name='Hospitalizations')
	kc_hosp = pd.read_csv('king-county-data-download/covid-data-daily-counts-latest-hospitalizations.csv')
	kc_hosp['Admission_Date'] = pd.to_datetime(kc_hosp['Admission_Date'])		# Not necessary when using `read_excel`
	kc_hosp = kc_hosp[kc_hosp['Admission_Date'].notnull()]
	kc_hosp['Moving_Average_7_Day'] = kc_hosp['Hospitalizations'].rolling(7).mean()

	#kc_test = pd.read_excel(kc_xlsx_file, sheet_name='Tests')
	kc_test = pd.read_csv('king-county-data-download/covid-data-daily-counts-latest-tests.csv')
	kc_test['Result_Date'] = pd.to_datetime(kc_test['Result_Date'])		# Not necessary when using `read_excel`
	kc_test = kc_test[kc_test['Result_Date'].notnull()]
	kc_test['Moving_Average_7_Day'] = kc_test['Tests'].rolling(7).mean()

	joined = kc.join(kc_test.set_index('Result_Date'), on='date')
	joined['positive_test_rate'] = joined['new_cases'] / joined['Tests']
	joined['positive_test_rate_moving_average_7_day'] = joined['positive_test_rate'].rolling(7).mean()

	# TODO: Return just one DataFrame
	return Data(cases_and_deaths=kc, hospitalizations=kc_hosp, tests=kc_test, positive_test_rate=joined)


def min_max_dates(date_serieses):
	# Hospitalizations started in King County prior to 3/1/2020, but all other data series are relevant after 3/1/2020.
	# Hard-code start date to 3/1/2020
	min_date = datetime.date(2020, 3, 1)
	max_date = None

	for date_series in date_serieses:
		series_min_date = date_series.min()
		series_max_date = date_series.max()

		# if min_date is None or series_min_date < min_date:
		# 	min_date = series_min_date
		if max_date is None or series_max_date > max_date:
			max_date = series_max_date

	return [min_date, max_date]


def plot_html(fig, date_range):
	fig.update_xaxes(
		range=date_range,
		showgrid=True
	)

	fig.update_layout(
		margin=go.layout.Margin(
			l=0,
			t=0,
			r=0,
			b=0
		),
		xaxis_showticklabels=True,
		xaxis_tickformat='%-m/%-d/%Y',
		legend=dict(
			orientation='h',
			xanchor='right',
			x=1
		)
	)

	config = {
		'staticPlot': True,
		'responsive': True
	}
	
	return fig.to_html(full_html=False, config=config, include_plotlyjs='cdn')


def format_date(date: datetime.date):
	return f'{date.month}/{date.day}/{date.year:4d}'


def plot_with_plotly(data: Data, nytimes_pull_date: datetime.date, king_county_pull_date: datetime.date):
	cols = plotly.colors.DEFAULT_PLOTLY_COLORS
	black = 'rgb(0, 0, 0)'

	axis_tickmark_font_size = 22
	subplot_title_font_size = 30

	date_range = min_max_dates([data.cases_and_deaths['date'], data.hospitalizations['Admission_Date'], data.tests['Result_Date'], data.positive_test_rate['date']])

	new_cases_fig = go.Figure()
	new_cases_fig.add_trace(
		go.Bar(
			name='Daily count',
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_cases'],
			marker=dict(color=cols[0])
		)
	)
	new_cases_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_cases_moving_average_7_day'],
			line=dict(width=2, color=black)
		)
	)

	hospitalizations_fig = go.Figure()
	hospitalizations_fig.add_trace(
		go.Bar(
			name='Daily count',
			x=data.hospitalizations['Admission_Date'],
			y=data.hospitalizations['Hospitalizations'],
			marker=dict(color=cols[1])
		)
	)
	hospitalizations_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.hospitalizations['Admission_Date'],
			y=data.hospitalizations['Moving_Average_7_Day'],
			line=dict(width=2, color=black)
		)
	)

	deaths_fig = go.Figure()
	deaths_fig.add_trace(
		go.Bar(
			name='Daily count',
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_deaths'],
			marker=dict(color=cols[2])
		)
	)
	deaths_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_deaths_moving_average_7_day'],
			line=dict(width=2, color=black)
		)
	)

	tests_fig = go.Figure()
	tests_fig.add_trace(
		go.Bar(
			name='Daily count',
			x=data.tests['Result_Date'],
			y=data.tests['Tests'],
			marker=dict(color=cols[3])
		)
	)
	tests_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.tests['Result_Date'],
			y=data.tests['Moving_Average_7_Day'],
			line=dict(width=2, color=black)
		)
	)

	positive_test_rate_fig = go.Figure()
	positive_test_rate_fig.add_trace(
		go.Bar(
			name='Daily count',
			x=data.positive_test_rate['date'],
			y=data.positive_test_rate['positive_test_rate'],
			marker=dict(color=cols[4])
		)
	)
	positive_test_rate_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.positive_test_rate['date'],
			y=data.positive_test_rate['positive_test_rate_moving_average_7_day'],
			line=dict(width=2, color=black)
		)
	)
	positive_test_rate_fig.update_yaxes(range=[0, 0.3])
	positive_test_rate_fig.update_layout(yaxis_tickformat='%')

	# Write wrapper HTML
	output_template = mako.template.Template(filename='output-template.html', output_encoding='utf-8')

	template_data = {
		'new_cases_plot': plot_html(new_cases_fig, date_range),
		'hospitalizations_plot': plot_html(hospitalizations_fig, date_range),
		'deaths_plot': plot_html(deaths_fig, date_range),
		'tests_plot': plot_html(tests_fig, date_range),
		'positive_test_rate_plot': plot_html(positive_test_rate_fig, date_range),
		'nytimes_pull_date': format_date(nytimes_pull_date),
		'king_county_pull_date': format_date(king_county_pull_date),
		'page_updated_date': format_date(datetime.date.today()),
	}

	output_file = open('output/output.html', 'wb')
	output_file.write(output_template.render(**template_data))


def run(*, nytimes_pull_date: datetime.date, king_county_pull_date: datetime.date):
	data = read_data()
	plot_with_plotly(data, nytimes_pull_date, king_county_pull_date)
