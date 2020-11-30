import datetime
import mako.template
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go

from plotly.subplots import make_subplots
from typing import NamedTuple


class DateRange(NamedTuple):
	min_date: datetime.date
	max_date: datetime.date


class KingCountyData(NamedTuple):
	positives: pd.DataFrame
	positives_last_good_date: datetime.date
	hospitalizations: pd.DataFrame
	deaths: pd.DataFrame
	tests: pd.DataFrame
	positive_test_rate: pd.DataFrame


def min_max_dates(date_serieses):
	min_date = None
	max_date = None

	for date_series in date_serieses:
		series_min_date = date_series.min()
		series_max_date = date_series.max()

		if min_date is None or series_min_date < min_date:
			min_date = series_min_date
		if max_date is None or series_max_date > max_date:
			max_date = series_max_date

	return DateRange(min_date, max_date)


def overlapping_date_range(range_1, range_2):
	min_date = range_1.min_date
	max_date = range_1.max_date

	if range_2.min_date > min_date:
		min_date = range_2.min_date
	if range_2.max_date < max_date:
		max_date = range_2.max_date

	return DateRange(min_date, max_date)


def read_nytimes_data(state: str, county: str):
	df = pd.read_csv('covid-19-data/us-counties.csv')

	nyt = df[(df['state'] == state) & (df['county'] == county)]
	nyt = nyt[['date', 'cases', 'deaths']]
	nyt['new_cases'] = nyt['cases'].diff().astype('Int64')
	nyt['new_deaths'] = nyt['deaths'].diff().astype('Int64')

	# Drop the first row with NaN diff values.
	nyt = nyt.drop(nyt.index[0])

	nyt['date'] = pd.to_datetime(nyt['date'])

	nyt['new_cases_moving_average_7_day'] = nyt['new_cases'].rolling(7).mean()
	nyt['new_deaths_moving_average_7_day'] = nyt['new_deaths'].rolling(7).mean()

	return nyt


def read_kc_data():
	nyt = read_nytimes_data(state='Washington', county='King')

	#kc_xlsx_file = 'king-county-data-download/covid-data-daily-counts-2020-09-08.xlsx'

	# `read_excel` appears to have a bug that silently drops recent data from the xlsx file, for some reason
	# For now, work around this by reading from CSV instead
	
	#kc_pos = pd.read_excel(kc_xlsx_file, sheet_name='Positives')
	kc_pos = pd.read_csv('king-county-data-download/daily-counts-and-rate-latest-positives.csv')
	kc_pos['Result_Date'] = pd.to_datetime(kc_pos['Result_Date'])		# Not necessary when using `read_excel`
	kc_pos = kc_pos[kc_pos['Result_Date'].notnull()]
	kc_pos['Moving_Average_7_Day'] = kc_pos['Positives'].rolling(7).mean()

	#kc_hosp = pd.read_excel(kc_xlsx_file, sheet_name='Hospitalizations')
	kc_hosp = pd.read_csv('king-county-data-download/daily-counts-and-rate-latest-hospitalizations.csv')
	kc_hosp['Admission_Date'] = pd.to_datetime(kc_hosp['Admission_Date'])		# Not necessary when using `read_excel`
	kc_hosp = kc_hosp[kc_hosp['Admission_Date'].notnull()]
	kc_hosp['Moving_Average_7_Day'] = kc_hosp['Hospitalizations'].rolling(7).mean()

	#kc_test = pd.read_excel(kc_xlsx_file, sheet_name='Tests')
	kc_test = pd.read_csv('king-county-data-download/daily-counts-and-rate-latest-tests.csv')
	kc_test['Result_Date'] = pd.to_datetime(kc_test['Result_Date'])		# Not necessary when using `read_excel`
	kc_test = kc_test[kc_test['Result_Date'].notnull()]
	kc_test['Moving_Average_7_Day'] = kc_test['People_Tested'].rolling(7).mean()
	
	#kc_deaths = pd.read_excel(kc_xlsx_file, sheet_name='Deaths')
	kc_deaths = pd.read_csv('king-county-data-download/daily-counts-and-rate-latest-deaths.csv')
	kc_deaths['Death_Date'] = pd.to_datetime(kc_deaths['Death_Date'])		# Not necessary when using `read_excel`
	kc_deaths = kc_deaths[kc_deaths['Death_Date'].notnull()]
	kc_deaths['Moving_Average_7_Day'] = kc_deaths['Deaths'].rolling(7).mean()

	joined = kc_pos.join(kc_test.set_index('Result_Date'), on='Result_Date', lsuffix='_pos', rsuffix='test')
	joined['positive_test_rate'] = joined['Positives'] / joined['People_Tested']
	joined['positive_test_rate_moving_average_7_day'] = joined['positive_test_rate'].rolling(7).mean()

	# Use NYT data to project recent days of new cases that haven't been reported by King County yet
	new_cases_date_range_kc = min_max_dates([kc_pos['Result_Date']])
	new_cases_date_range_nyt = min_max_dates([nyt['date']])

	if new_cases_date_range_nyt.max_date > new_cases_date_range_kc.max_date:
		date_range_overlap = overlapping_date_range(new_cases_date_range_nyt, new_cases_date_range_kc)

		new_cases_kc = kc_pos[(kc_pos['Result_Date'] >= date_range_overlap.min_date) & (kc_pos['Result_Date'] <= date_range_overlap.max_date)]
		new_cases_nyt = nyt[(nyt['date'] >= date_range_overlap.min_date) & (nyt['date'] <= date_range_overlap.max_date)]

		ratio = new_cases_kc['Positives'].sum() / new_cases_nyt['new_cases'].sum()

		nyt_subset = nyt[(nyt['date']) > new_cases_date_range_kc.max_date].copy()
		nyt_subset['Positives_Projected'] = nyt_subset['new_cases'] * ratio
		nyt_subset = nyt_subset[['date', 'Positives_Projected']]

		kc_pos = kc_pos.join(nyt_subset.set_index('date'), on='Result_Date', how='outer')

		kc_pos['Positives'] = np.where(kc_pos['Positives'].isnull(), kc_pos['Positives_Projected'], kc_pos['Positives'])

	# TODO: Return just one DataFrame
	return KingCountyData(
		positives=kc_pos,
		positives_last_good_date=new_cases_date_range_kc.max_date,
		hospitalizations=kc_hosp,
		deaths=kc_deaths,
		tests=kc_test,
		positive_test_rate=joined)


def plot_html(fig, date_range):
	fig.update_xaxes(
		fixedrange=True,
		# Disable pan/zoom because otherwise the output page is unusable on mobile
		range=[date_range.min_date, date_range.max_date],
		showgrid=True
	)

	fig.update_yaxes(
		# Disable pan/zoom because otherwise the output page is unusable on mobile
		fixedrange=True
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
		'displayModeBar': False,
		'responsive': True,
		#'staticPlot': True,
		'scrollZoom': False
	}
	
	return fig.to_html(full_html=False, config=config, include_plotlyjs='cdn')


def format_date(date: datetime.date):
	return f'{date.month}/{date.day}/{date.year:4d}'


def plot_with_plotly(
	data,
	nytimes_pull_date: str,
	king_county_pull_date: str,
	output_file_name: str):

	cols = plotly.colors.DEFAULT_PLOTLY_COLORS
	black = 'rgb(0, 0, 0)'
	recent_highlight_color = 'rgba(0, 0, 0, 0.15)'

	axis_tickmark_font_size = 22
	subplot_title_font_size = 30

	date_range_series = [data.positives['Result_Date'], data.hospitalizations['Admission_Date'], data.tests['Result_Date'], data.positive_test_rate['Result_Date']]

	date_range = min_max_dates(date_range_series)

	# Hospitalizations started in King County prior to 3/1/2020, but all other data series are relevant after 3/1/2020.
	# Hard-code start date to 3/1/2020
	date_range = DateRange(min_date=datetime.date(2020, 3, 1), max_date=date_range.max_date)

	new_cases_fig = go.Figure()
	new_cases_fig.add_trace(
		go.Bar(
			name='Daily count',
			x=data.positives['Result_Date'],
			y=data.positives['Positives'],
			marker=dict(color=cols[0])
		)
	)
	new_cases_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.positives['Result_Date'],
			y=data.positives['Moving_Average_7_Day'],
			line=dict(width=2, color=black)
		)
	)
	new_cases_fig.add_shape(
		type='rect',
		xref='x',
		yref='paper',
		x0=data.positives_last_good_date,
		y0=0,
		x1=date_range.max_date,
		y1=1,
		line=dict(color='rgba(0,0,0,0)',width=3,),
		fillcolor=recent_highlight_color,
		layer='below')

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
			x=data.deaths['Death_Date'],
			y=data.deaths['Deaths'],
			marker=dict(color=cols[2])
		)
	)
	deaths_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.deaths['Death_Date'],
			y=data.deaths['Moving_Average_7_Day'],
			line=dict(width=2, color=black)
		)
	)

	tests_fig = go.Figure()
	tests_fig.add_trace(
		go.Bar(
			name='Daily count',
			x=data.tests['Result_Date'],
			y=data.tests['People_Tested'],
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
			x=data.positive_test_rate['Result_Date'],
			y=data.positive_test_rate['positive_test_rate'],
			marker=dict(color=cols[4])
		)
	)
	positive_test_rate_fig.add_trace(
		go.Scatter(
			name='7-day average',
			x=data.positive_test_rate['Result_Date'],
			y=data.positive_test_rate['positive_test_rate_moving_average_7_day'],
			line=dict(width=2, color=black)
		)
	)
	positive_test_rate_fig.update_yaxes(range=[0, 0.4])
	positive_test_rate_fig.update_layout(yaxis_tickformat='%')

	# Write wrapper HTML
	output_template = mako.template.Template(filename='output-template.html', output_encoding='utf-8')

	template_data = {
		'new_cases_plot': plot_html(new_cases_fig, date_range),
		'deaths_plot': plot_html(deaths_fig, date_range),
		'nytimes_pull_date': format_date(pd.to_datetime(nytimes_pull_date)),
		'page_updated_date': format_date(datetime.date.today()),
		'plot_county': True,
		'hospitalizations_plot': plot_html(hospitalizations_fig, date_range),
		'tests_plot': plot_html(tests_fig, date_range),
		'positive_test_rate_plot': plot_html(positive_test_rate_fig, date_range),
		'king_county_pull_date': format_date(pd.to_datetime(king_county_pull_date)),
	}

	output_file = open(f'output/{output_file_name}', 'wb')
	output_file.write(output_template.render(**template_data))


def run(*, nytimes_pull_date: str, king_county_pull_date: str):
	kc = read_kc_data()

	plot_with_plotly(kc, nytimes_pull_date, king_county_pull_date, output_file_name='output.html')
