use clap::error::Result;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::widgets::Paragraph;
extern crate log;
use itertools::Itertools;
use ratatui::{
    layout::{Constraint, Flex, Layout, Rect},
    prelude::*,
    widgets::{Axis, Block, Borders, Chart, Clear, Dataset, GraphType, List, ListItem, ListState},
    Frame,
};
use std::{
    io,
    time::{Duration, Instant},
};

use crate::data_handler::DeviceData;

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use tui_logger::*;
pub async fn run_tui(address: &str, remote: bool) -> tokio::io::Result<()> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let tick_rate = Duration::from_millis(100);
    let app = App::new();
    let res = run_app(&mut terminal, app, tick_rate, address, remote);

    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    if let Err(err) = res {
        println!("{err:?}");
    }
    Ok(())
}

#[derive(Debug, Serialize, Deserialize)]
struct ServerResponse {
    #[serde(flatten)]
    response: HashMap<String, DeviceData>,
}

struct StreamReference {
    device_index: usize,
    stream_index: usize,
}

struct DataStream {
    name: String,
    points: Vec<(f64, f64)>,
}

struct Device {
    name: String,
    streams: Vec<DataStream>,
}

struct App {
    devices: Vec<Device>,
    devices_state: ListState,
    streams_state: ListState,
    x_axis_stream: Option<StreamReference>,
    y_axis_stream: Option<StreamReference>,
    log_messages: Vec<String>,
    connection_status: bool,
    current_device_streams: Vec<String>,
    show_popup: bool,
}

impl App {
    fn new() -> App {
        let mut devices_state = ListState::default();
        devices_state.select(Some(0));

        let devices: Vec<Device> = vec![];

        let current_device_streams = if !devices.is_empty() {
            devices[0].streams.iter().map(|s| s.name.clone()).collect()
        } else {
            vec![]
        };

        App {
            devices,
            devices_state,
            streams_state: ListState::default(),
            x_axis_stream: None,
            y_axis_stream: None,
            log_messages: vec!["System initialized".to_string()],
            current_device_streams,
            connection_status: true,
            show_popup: false,
        }
    }
    pub fn fetch_server_data(&mut self, addr: &str) -> Result<(), Box<dyn std::error::Error>> {
        let mut stream = match TcpStream::connect(addr) {
            Ok(stream) => stream,
            Err(_) => {
                match self.connection_status {
                    true => {
                        log::warn!(
                            "Not connected to address {}. Data server is not running.",
                            addr,
                        );
                        self.connection_status = false;
                    }
                    false => {}
                };
                return Ok(());
            }
        };

        stream.write_all(b"GET_DATASTREAM\n")?;
        stream.flush()?;

        let mut reader = BufReader::new(stream);
        let mut response = String::new();

        match reader.read_line(&mut response) {
            Ok(0) => {
                log::info!("Experiment host closed{}", addr);
            }
            Ok(_) => {
                let trimmed = response.trim();
                if !trimmed.is_empty() {
                    match serde_json::from_str::<ServerResponse>(trimmed) {
                        Ok(server_response) => {
                            self.devices = server_response
                                .response
                                .into_iter()
                                .sorted_by_key(|(device_key, _)| device_key.clone())
                                .map(|(device_key, device_data)| {
                                    let streams: Vec<DataStream> = device_data
                                        .measurements
                                        .into_iter()
                                        .sorted_by_key(|(stream_name, _)| stream_name.clone())
                                        .map(|(stream_name, values)| DataStream {
                                            name: stream_name,
                                            points: values
                                                .into_iter()
                                                .enumerate()
                                                .map(|(idx, value)| (idx as f64, value))
                                                .collect(),
                                        })
                                        .collect();

                                    Device {
                                        name: device_key,
                                        streams,
                                    }
                                })
                                .collect();
                        }
                        Err(e) => log::error!("JSON Deserialization Error: {}", e),
                    }
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::ConnectionReset => {
                log::info!("PyFex Server shutdown, you can exit the TUI now");
            }
            Err(e) => {
                log::error!("Read Error: {}", e);
            }
        }

        Ok(())
    }

    fn kill_server(&mut self, addr: &str) {
        let mut stream = match TcpStream::connect(addr) {
            Ok(stream) => stream,
            Err(_) => {
                match self.connection_status {
                    true => {
                        log::warn!(
                            "Not connected to address {}. Data server is not running.",
                            addr,
                        );
                        self.connection_status = false;
                    }
                    false => {}
                };
                return;
            }
        };

        let _ = stream.write_all(b"KILL\n");
        let _ = stream.flush();

        let mut reader = BufReader::new(stream);
        let mut response = String::new();

        match reader.read_line(&mut response) {
            Ok(0) => {
                log::info!("Experiment host closed{}", addr);
            }
            Ok(_) => {
                let trimmed = response.trim();
                log::info!("{:?}", trimmed)
            }
            Err(e) if e.kind() == std::io::ErrorKind::ConnectionReset => {
                log::info!("PyFex Server shutdown, you can exit the TUI now");
            }
            Err(e) => {
                log::error!("Read Error: {}", e);
            }
        }
    }
    fn pause_server(&mut self, addr: &str) {
        let mut stream = match TcpStream::connect(addr) {
            Ok(stream) => stream,
            Err(_) => {
                match self.connection_status {
                    true => {
                        log::warn!(
                            "Not connected to address {}. Data server is not running.",
                            addr,
                        );
                        self.connection_status = false;
                    }
                    false => {}
                };
                return;
            }
        };

        let _ = stream.write_all(b"PAUSE_STATE\n");
        let _ = stream.flush();

        let mut reader = BufReader::new(stream);
        let mut response = String::new();

        match reader.read_line(&mut response) {
            Ok(0) => {
                log::info!("Experiment host closed{}", addr);
            }
            Ok(_) => {
                let trimmed = response.trim();
                log::info!("{:?}", trimmed)
            }
            Err(e) => {
                log::error!("Read Error: {}", e);
            }
        }
    }

    fn resume_server(&mut self, addr: &str) {
        let mut stream = match TcpStream::connect(addr) {
            Ok(stream) => stream,
            Err(_) => {
                match self.connection_status {
                    true => {
                        log::warn!(
                            "Not connected to address {}. Data server is not running.",
                            addr,
                        );
                        self.connection_status = false;
                    }
                    false => {}
                };
                return;
            }
        };

        let _ = stream.write_all(b"RESUME_STATE\n");
        let _ = stream.flush();

        let mut reader = BufReader::new(stream);
        let mut response = String::new();

        match reader.read_line(&mut response) {
            Ok(0) => {
                log::info!("Experiment host closed{}", addr);
            }
            Ok(_) => {
                let trimmed = response.trim();
                log::info!("{:?}", trimmed)
            }
            Err(e) => {
                log::error!("Read Error: {}", e);
            }
        }
    }
    fn set_x_axis(&mut self) {
        if let Some(device_idx) = self.devices_state.selected() {
            if let Some(stream_idx) = self.streams_state.selected() {
                self.x_axis_stream = Some(StreamReference {
                    device_index: device_idx,
                    stream_index: stream_idx,
                });

                let device = &self.devices[device_idx];
                let stream = &device.streams[stream_idx];

                self.log_messages
                    .push(format!("Set X-axis: {} - {}", device.name, stream.name));
            }
        }
    }

    fn set_y_axis(&mut self) {
        if let Some(device_idx) = self.devices_state.selected() {
            if let Some(stream_idx) = self.streams_state.selected() {
                self.y_axis_stream = Some(StreamReference {
                    device_index: device_idx,
                    stream_index: stream_idx,
                });

                let device = &self.devices[device_idx];
                let stream = &device.streams[stream_idx];

                self.log_messages
                    .push(format!("Set Y-axis: {} - {}", device.name, stream.name));
            }
        }
    }

    fn on_tick(&mut self, address: &str) {
        let _ = self.fetch_server_data(address);
    }

    fn next_device(&mut self) {
        let i = match self.devices_state.selected() {
            Some(i) => {
                if i >= self.devices.len() - 1 {
                    0
                } else {
                    i + 1
                }
            }
            None => 0,
        };
        self.devices_state.select(Some(i));
        self.update_current_device_streams();
    }

    fn update_current_device_streams(&mut self) {
        if let Some(device_idx) = self.devices_state.selected() {
            if !self.devices.is_empty() && device_idx < self.devices.len() {
                self.current_device_streams = self.devices[device_idx]
                    .streams
                    .iter()
                    .map(|s| s.name.clone())
                    .collect();

                self.streams_state
                    .select(if !self.current_device_streams.is_empty() {
                        Some(0)
                    } else {
                        None
                    });
            } else {
                self.current_device_streams = vec![];
                self.streams_state.select(None);
            }
        }
    }

    fn next_stream(&mut self) {
        if let Some(device_idx) = self.devices_state.selected() {
            let num_streams = self.devices[device_idx].streams.len();

            if num_streams == 0 {
                return;
            }

            let i = match self.streams_state.selected() {
                Some(i) => {
                    if i >= num_streams - 1 {
                        0
                    } else {
                        i + 1
                    }
                }
                None => 0,
            };
            self.streams_state.select(Some(i));
        }
    }

    fn previous_stream(&mut self) {
        if let Some(device_idx) = self.devices_state.selected() {
            let num_streams = self.devices[device_idx].streams.len();

            if num_streams == 0 {
                return;
            }

            let i = match self.streams_state.selected() {
                Some(i) => {
                    if i == 0 {
                        num_streams - 1
                    } else {
                        i - 1
                    }
                }
                None => 0,
            };
            self.streams_state.select(Some(i));
        }
    }

    fn previous_device(&mut self) {
        let i = match self.devices_state.selected() {
            Some(i) => {
                if i == 0 {
                    self.devices.len() - 1
                } else {
                    i - 1
                }
            }
            None => 0,
        };
        self.devices_state.select(Some(i));
        self.update_current_device_streams();
    }
}

fn run_app<B: Backend>(
    terminal: &mut Terminal<B>,
    mut app: App,
    tick_rate: Duration,
    address: &str,
    remote: bool,
) -> io::Result<()> {
    let mut last_tick = Instant::now();
    loop {
        terminal.draw(|f| ui(f, &mut app))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        if crossterm::event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    match key.code {
                        KeyCode::Char('q') => match remote {
                            true => return Ok(()),

                            false => {
                                app.kill_server(&address);
                                return Ok(());
                            }
                        },
                        KeyCode::Down => app.next_device(),
                        KeyCode::Up => app.previous_device(),
                        KeyCode::Right => app.next_stream(),
                        KeyCode::Left => app.previous_stream(),
                        KeyCode::Char('x') => app.set_x_axis(),
                        KeyCode::Char('k') => app.kill_server(&address),
                        KeyCode::Char('y') => app.set_y_axis(),
                        KeyCode::Char('m') => app.show_popup = !app.show_popup,
                        KeyCode::Char('c') => {
                            app.x_axis_stream = None;
                            app.y_axis_stream = None;
                            log::info!("Cleared axis selections");
                        }
                        KeyCode::Char('p') => {
                            app.pause_server(&address);
                        }
                        KeyCode::Char('r') => {
                            app.resume_server(&address);
                        }
                        _ => {}
                    }
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            app.on_tick(address);
            last_tick = Instant::now();
        }
    }
}

fn ui(f: &mut Frame, app: &mut App) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage(50),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
        ])
        .split(f.area());

    let lists_chunk = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(chunks[1]);

    if let (Some(x_ref), Some(y_ref)) = (&app.x_axis_stream, &app.y_axis_stream) {
        let x_stream = &app.devices[x_ref.device_index].streams[x_ref.stream_index];
        let y_stream = &app.devices[y_ref.device_index].streams[y_ref.stream_index];

        let points: Vec<(f64, f64)> = x_stream
            .points
            .iter()
            .zip(y_stream.points.iter())
            .map(|((_, x), (_, y))| (*x, *y))
            .collect();

        if !points.is_empty() {
            let datasets = vec![Dataset::default()
                .marker(symbols::Marker::Braille)
                .graph_type(GraphType::Line)
                .style(Style::default().fg(Color::Cyan))
                .data(&points)];

            let x_values: Vec<f64> = points.iter().map(|(x, _)| *x).collect();
            let y_values: Vec<f64> = points.iter().map(|(_, y)| *y).collect();

            let x_min = x_values.iter().fold(f64::INFINITY, |a, &b| a.min(b));
            let x_max = x_values.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
            let y_min = y_values.iter().fold(f64::INFINITY, |a, &b| a.min(b));
            let y_max = y_values.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));

            let x_margin = (x_max - x_min) * 0.1;
            let y_margin = (y_max - y_min) * 0.1;

            let x_labels: Vec<Span> = (0..=4)
                .map(|i| {
                    let val = x_min + (i as f64) * (x_max - x_min) / 4.0;
                    Span::styled(format!("{:.2}", val), Style::default().fg(Color::White))
                })
                .collect();

            let y_labels: Vec<Span> = (0..=4)
                .map(|i| {
                    let val = y_min + (i as f64) * (y_max - y_min) / 4.0;
                    Span::styled(format!("{:.2}", val), Style::default().fg(Color::White))
                })
                .collect();
            let chart = Chart::new(datasets)
                .block(
                    Block::default()
                        .title(format!("{} vs {}", x_stream.name, y_stream.name))
                        .borders(Borders::ALL),
                )
                .x_axis(
                    Axis::default()
                        .title(x_stream.name.clone())
                        .bounds([x_min - x_margin, x_max + x_margin])
                        .labels(x_labels),
                )
                .y_axis(
                    Axis::default()
                        .title(y_stream.name.clone())
                        .bounds([y_min - y_margin, y_max + y_margin])
                        .labels(y_labels),
                );
            f.render_widget(chart, chunks[0]);
        }
    } else {
        let block = Block::default()
            .title("Select X and Y axes to view data")
            .borders(Borders::ALL);
        f.render_widget(block, chunks[0]);
    }

    let devices: Vec<ListItem> = app
        .devices
        .iter()
        .enumerate()
        .map(|(idx, device)| {
            let prefix = match (app.x_axis_stream.as_ref(), app.y_axis_stream.as_ref()) {
                (Some(x_ref), Some(y_ref))
                    if x_ref.device_index == idx && y_ref.device_index == idx =>
                {
                    "X,Y"
                }
                (Some(x_ref), _) if x_ref.device_index == idx => "X",
                (_, Some(y_ref)) if y_ref.device_index == idx => "Y",
                _ => "  ",
            };
            ListItem::new(format!("[{}] {}", prefix, device.name))
                .style(Style::default().fg(Color::Green))
        })
        .collect();

    let devices_list = List::new(devices)
        .block(
            Block::default()
                .title("Connected Devices (↑↓ to navigate)")
                .borders(Borders::ALL),
        )
        .highlight_style(
            Style::default()
                .bg(Color::DarkGray)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol(">> ");

    f.render_stateful_widget(devices_list, lists_chunk[0], &mut app.devices_state);

    if let Some(device_idx) = app.devices_state.selected() {
        let device = &app.devices[device_idx];
        let streams: Vec<ListItem> = device
            .streams
            .iter()
            .enumerate()
            .map(|(idx, stream)| {
                let prefix = match (app.x_axis_stream.as_ref(), app.y_axis_stream.as_ref()) {
                    (Some(x_ref), Some(y_ref))
                        if x_ref.device_index == device_idx
                            && x_ref.stream_index == idx
                            && y_ref.device_index == device_idx
                            && y_ref.stream_index == idx =>
                    {
                        "X,Y"
                    }
                    (Some(x_ref), _)
                        if x_ref.device_index == device_idx && x_ref.stream_index == idx =>
                    {
                        "X"
                    }
                    (_, Some(y_ref))
                        if y_ref.device_index == device_idx && y_ref.stream_index == idx =>
                    {
                        "Y"
                    }
                    _ => "  ",
                };
                ListItem::new(format!("[{}] {}", prefix, stream.name))
                    .style(Style::default().fg(Color::Yellow))
            })
            .collect();

        let streams_list = List::new(streams)
            .block(
                Block::default()
                    .title("Data Streams (←→ to navigate, x/y to set axes)")
                    .borders(Borders::ALL),
            )
            .highlight_style(
                Style::default()
                    .bg(Color::DarkGray)
                    .add_modifier(Modifier::BOLD),
            )
            .highlight_symbol(">> ");

        f.render_stateful_widget(streams_list, lists_chunk[1], &mut app.streams_state);
    }

    let tui_logger = TuiLoggerWidget::default()
        .style_error(Style::default().fg(Color::Red))
        .style_debug(Style::default().fg(Color::Green))
        .style_warn(Style::default().fg(Color::Yellow))
        .style_trace(Style::default().fg(Color::Magenta))
        .style_info(Style::default().fg(Color::Cyan))
        .block(Block::default().title("System Log").borders(Borders::ALL));
    f.render_widget(tui_logger, chunks[2]);

    let controls = create_controls_widget();
    if app.show_popup {
        let block = Block::bordered().title("Popup");
        let area = popup_area(area, 60, 40);
        f.render_widget(Clear, area); //this clears out the background
        f.render_widget(block, area);
        f.render_widget(controls, area);
    }
}
fn create_controls_widget() -> impl Widget {
    let control_text = vec![
        vec![Span::styled(
            "Navigation:",
            Style::default().add_modifier(Modifier::BOLD),
        )],
        vec![Span::raw("↑/↓     - Navigate devices")],
        vec![Span::raw("←/→     - Navigate streams")],
        vec![Span::raw("")],
        vec![Span::styled(
            "Actions:",
            Style::default().add_modifier(Modifier::BOLD),
        )],
        vec![Span::raw("c      - Clear Plot")],
        vec![Span::raw("x      - Set x-axis stream")],
        vec![Span::raw("y      - Set y-axis stream")],
        vec![Span::raw(
            "k      - Kill Python proces (end the experiment)",
        )],
        vec![Span::raw("p      - pause the currently running experiment")],
        vec![Span::raw(
            "r      - resume the currently running experiment",
        )],
        vec![Span::raw("")],
        vec![Span::styled(
            "System:",
            Style::default().add_modifier(Modifier::BOLD),
        )],
        vec![Span::raw("q  - Quit Experiment / Exit remote viewer")],
    ];

    let text: Vec<Line> = control_text.into_iter().map(Line::from).collect();

    Paragraph::new(text)
        .block(Block::default().title("Controls").borders(Borders::ALL))
        .style(Style::default().fg(Color::White))
        .alignment(Alignment::Left)
}

fn popup_area(area: Rect, percent_x: u16, percent_y: u16) -> Rect {
    let vertical = Layout::vertical([Constraint::Percentage(percent_y)]).flex(Flex::Center);
    let horizontal = Layout::horizontal([Constraint::Percentage(percent_x)]).flex(Flex::Center);
    let [area] = vertical.areas(area);
    let [area] = horizontal.areas(area);
    area
}
