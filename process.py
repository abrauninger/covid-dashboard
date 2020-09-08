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

	kc_xlsx_file = 'king-county-data-download/covid-data-daily-counts-2020-08-31.xlsx'

	kc_hosp = pd.read_excel(kc_xlsx_file, sheet_name='Hospitalizations')
	kc_hosp = kc_hosp[kc_hosp['Admission_Date'].notnull()]
	kc_hosp['Moving_Average_7_Day'] = kc_hosp['Hospitalizations'].rolling(7).mean()

	kc_test = pd.read_excel(kc_xlsx_file, sheet_name='Tests')
	kc_test = kc_test[kc_test['Result_Date'].notnull()]
	kc_test['Moving_Average_7_Day'] = kc_test['Tests'].rolling(7).mean()

	joined = kc.join(kc_test.set_index('Result_Date'), on='date')
	joined['positive_test_rate'] = joined['new_cases'] / joined['Tests']
	joined['positive_test_rate_moving_average_7_day'] = joined['positive_test_rate'].rolling(7).mean()

	# TODO: Return just one DataFrame
	return Data(cases_and_deaths=kc, hospitalizations=kc_hosp, tests=kc_test, positive_test_rate=joined)


def plot_html(fig):
	config = {'staticPlot': True}
	return fig.to_html(full_html=False, config=config, include_plotlyjs='cdn')


def plot_with_plotly(data: Data):
	cols = plotly.colors.DEFAULT_PLOTLY_COLORS
	black = 'rgb(0, 0, 0)'

	axis_tickmark_font_size = 22
	subplot_title_font_size = 30

	new_cases_fig = go.Figure()
	new_cases_fig.add_trace(
		go.Bar(
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_cases'],
			marker=dict(color=cols[0])
		)
	)
	new_cases_fig.add_trace(
		go.Scatter(
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_cases_moving_average_7_day'],
			line=dict(width=2, color=black)
		)
	)

	hospitalizations_fig = go.Figure()
	hospitalizations_fig.add_trace(
		go.Bar(
			x=data.hospitalizations['Admission_Date'],
			y=data.hospitalizations['Hospitalizations'],
			marker=dict(color=cols[1])
		)
	)
	hospitalizations_fig.add_trace(
		go.Scatter(
			x=data.hospitalizations['Admission_Date'],
			y=data.hospitalizations['Moving_Average_7_Day'],
			line=dict(width=2, color=black)
		)
	)

	deaths_fig = go.Figure()
	deaths_fig.add_trace(
		go.Bar(
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_deaths'],
			marker=dict(color=cols[2])
		)
	)
	deaths_fig.add_trace(
		go.Scatter(
			x=data.cases_and_deaths['date'],
			y=data.cases_and_deaths['new_deaths_moving_average_7_day'],
			line=dict(width=2, color=black)
		)
	)

	tests_fig = go.Figure()
	tests_fig.add_trace(
		go.Bar(
			x=data.tests['Result_Date'],
			y=data.tests['Tests'],
			marker=dict(color=cols[3])
		)
	)
	tests_fig.add_trace(
		go.Scatter(
			x=data.tests['Result_Date'],
			y=data.tests['Moving_Average_7_Day'],
			line=dict(width=2, color=black)
		)
	)

	positive_test_rate_fig = go.Figure()
	positive_test_rate_fig.add_trace(
		go.Bar(
			x=data.positive_test_rate['date'],
			y=data.positive_test_rate['positive_test_rate'],
			marker=dict(color=cols[4])
		)
	)
	positive_test_rate_fig.add_trace(
		go.Scatter(
			x=data.positive_test_rate['date'],
			y=data.positive_test_rate['positive_test_rate_moving_average_7_day'],
			line=dict(width=2, color=black)
		)
	)
	positive_test_rate_fig.update_yaxes(range=[0, 0.3])

	# fig.update_layout(
	# 	title_text='COVID-19 metrics in King County, WA',
	# 	showlegend=False,
	# 	titlefont=dict(size=40)
	# )

	# By default, only the bottom subplot in the stack has X-axis labels (dates).
	# Show dates on each subplot's X-axis.
	# fig.update_layout(
	# 	xaxis_showticklabels=True,
	# 	xaxis2_showticklabels=True,
	# 	xaxis3_showticklabels=True,
	# 	xaxis4_showticklabels=True,
	# 	xaxis5_showticklabels=True,
	# 	xaxis_tickfont=dict(size=axis_tickmark_font_size),
	# 	xaxis2_tickfont=dict(size=axis_tickmark_font_size),
	# 	xaxis3_tickfont=dict(size=axis_tickmark_font_size),
	# 	xaxis4_tickfont=dict(size=axis_tickmark_font_size),
	# 	xaxis5_tickfont=dict(size=axis_tickmark_font_size),
	# )

	# for annotation in fig['layout']['annotations']:
	# 	annotation['font']['size'] = subplot_title_font_size

	# fig.write_html('output/figures.html', config)

	# Write wrapper HTML
	# TODO: Do we really need a templating engine?  If the HTML stays completely static, just copy the "template" file to output.
	output_template = mako.template.Template(filename='output-template.html', output_encoding='utf-8')

	template_data = {
		'new_cases_plot': plot_html(new_cases_fig),
		'hospitalizations_plot': plot_html(hospitalizations_fig),
		'deaths_plot': plot_html(deaths_fig),
		'tests_plot': plot_html(tests_fig),
		'positive_test_rate_plot': plot_html(positive_test_rate_fig),
	}

	output_file = open('output/output.html', 'wb')
	output_file.write(output_template.render(**template_data))


def run():
	data = read_data()
	plot_with_plotly(data)
