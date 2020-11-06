import datetime
import mako.template
import pandas as pd
import plotly
import plotly.graph_objs as go

from plotly.subplots import make_subplots
from typing import NamedTuple


class Data(NamedTuple):
	cases_and_deaths: pd.DataFrame


def read_data():
	df = pd.read_csv('covid-19-data/us-counties.csv')

	sd = df[(df['state'] == 'California') & (df['county'] == 'San Diego')]
	sd = sd[['date', 'cases', 'deaths']]
	sd['new_cases'] = sd['cases'].diff().astype('Int64')
	sd['new_deaths'] = sd['deaths'].diff().astype('Int64')

	# Drop the first row with NaN diff values.
	sd = sd.drop(sd.index[0])

	sd['date'] = pd.to_datetime(sd['date'])

	sd['new_cases_moving_average_7_day'] = sd['new_cases'].rolling(7).mean()
	sd['new_deaths_moving_average_7_day'] = sd['new_deaths'].rolling(7).mean()

	# TODO: Return just one DataFrame
	return Data(cases_and_deaths=sd)


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
		fixedrange=True,
		# Disable pan/zoom because otherwise the output page is unusable on mobile
		range=date_range,
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


def plot_with_plotly(data: Data, nytimes_pull_date: str):
	cols = plotly.colors.DEFAULT_PLOTLY_COLORS
	black = 'rgb(0, 0, 0)'

	axis_tickmark_font_size = 22
	subplot_title_font_size = 30

	date_range = min_max_dates([data.cases_and_deaths['date']])

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

	# Write wrapper HTML
	output_template = mako.template.Template(filename='output-template-san-diego.html', output_encoding='utf-8')

	template_data = {
		'new_cases_plot': plot_html(new_cases_fig, date_range),
		'deaths_plot': plot_html(deaths_fig, date_range),
		'nytimes_pull_date': format_date(pd.to_datetime(nytimes_pull_date)),
		'page_updated_date': format_date(datetime.date.today()),
	}

	output_file = open('output/output-san-diego.html', 'wb')
	output_file.write(output_template.render(**template_data))


def run(*, nytimes_pull_date: str):
	data = read_data()
	plot_with_plotly(data, nytimes_pull_date)
