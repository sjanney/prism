package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/progress"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "github.com/sjanney/prism/proto"
)

type state int

const (
	stateLoading state = iota // Initial Loading Screen
	stateHome
	stateSearch
	stateIndex
	stateConnectDB
	stateSettings
	statePro
	stateCloudConfig // Cloud: Configure AWS/Azure
	stateBenchmark   // Developer Mode: Benchmarks & Diagnostics
)

// Notification types for the sidebar
type NotificationType int

const (
	NotifyInfo NotificationType = iota
	NotifySuccess
	NotifyWarning
	NotifyError
)

// Notification represents a single notification in the sidebar
type Notification struct {
	Type      NotificationType
	Message   string
	Timestamp time.Time
}

type sysInfoMsg *pb.GetSystemInfoResponse

// Main Model
type model struct {
	client pb.PrismServiceClient
	conn   *grpc.ClientConn
	state  state
	err    error
	width  int
	height int

	// Home / Dashboard
	dashboardOptions []string
	dashboardCursor  int
	stats            *pb.DatasetMetadata
	loadingStats     bool

	// Connect DB
	dbInput    textinput.Model
	dbStatus   string
	connecting bool

	// Search
	searchInput textinput.Model
	results     []*pb.SearchResult
	cursor      int
	page        int
	searching   bool

	// Global Spinner
	spinner spinner.Model

	// Loading Screen
	loadingPercent float64
	loadingLog     string

	// Index
	pathInput    textinput.Model
	progress     progress.Model
	indexing     bool
	indexStatus  string
	indexCurrent int64
	indexTotal   int64
	// Settings / System Info
	sysInfo    *pb.GetSystemInfoResponse
	loadingSys bool

	// Pro
	licenseInput textinput.Model
	proStatus    string
	activating   bool

	// Benchmark & Diagnostics
	benchmarkReport   *pb.BenchmarkReport
	benchmarking      bool
	benchmarkPhase    string
	benchmarkProgress string
	devMode           bool

	// Cloud Config

	cloudProvider   int // 0=AWS, 1=Azure
	awsAccessKey    textinput.Model
	awsSecretKey    textinput.Model
	awsRegion       textinput.Model
	azureConnStr    textinput.Model
	cloudStatus     string
	savingCloud     bool
	cloudFocusIndex int // 0-2 for AWS, 0-0 for Azure

	// Notifications
	notifications []Notification

	// Index stats (enhanced)
	indexSkipped int64
	indexETA     int32
}

func initialModel() model {
	si := textinput.New()
	si.Placeholder = "Search query (e.g. 'red car')"
	si.CharLimit = 156
	si.Width = 60
	si.TextStyle = inputPromptStyle

	pi := textinput.New()
	pi.Placeholder = "/absolute/path/to/dataset"
	pi.CharLimit = 256
	pi.Width = 60

	di := textinput.New()
	di.Placeholder = "prism.db"
	di.CharLimit = 256
	di.Width = 60

	prog := progress.New(progress.WithDefaultGradient())
	prog.Width = 50

	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	li := textinput.New()
	li.Placeholder = "PRISM-PRO-XXXX-XXXX"
	li.CharLimit = 36
	li.Width = 40
	li.TextStyle = inputPromptStyle

	// Cloud Inputs
	// AWS
	awsAk := textinput.New()
	awsAk.Placeholder = "AWS Access Key ID"
	awsAk.CharLimit = 128
	awsAk.Width = 50

	awsSk := textinput.New()
	awsSk.Placeholder = "AWS Secret Access Key"
	awsSk.EchoMode = textinput.EchoPassword
	awsSk.CharLimit = 128
	awsSk.Width = 50

	awsReg := textinput.New()
	awsReg.Placeholder = "Region (e.g. us-east-1)"
	awsReg.CharLimit = 32
	awsReg.Width = 20

	// Azure
	azConn := textinput.New()
	azConn.Placeholder = "Azure Storage Connection String"
	azConn.EchoMode = textinput.EchoPassword
	azConn.CharLimit = 512
	azConn.Width = 60

	return model{
		state:            stateLoading,
		dashboardOptions: []string{"Search", "Ingest Data", "Connect Database", "Settings"},
		dashboardCursor:  0,
		searchInput:      si,
		pathInput:        pi,
		dbInput:          di,

		progress:       prog,
		spinner:        s,
		loadingStats:   true,
		loadingPercent: 0,
		loadingLog:     "Initializing...",

		licenseInput: li,

		awsAccessKey:  awsAk,
		awsSecretKey:  awsSk,
		awsRegion:     awsReg,
		azureConnStr:  azConn,
		cloudProvider: 0, // Default AWS

		notifications: []Notification{
			{Type: NotifyInfo, Message: "Prism initialized", Timestamp: time.Now()},
		},
	}
}

// Tick for loading simulation
type tickMsg time.Time

func tickCmd() tea.Cmd {
	return tea.Tick(time.Millisecond*100, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func (m model) Init() tea.Cmd {
	return tea.Batch(
		textinput.Blink,
		m.spinner.Tick,
		tickCmd(), // Start simulated loading
		connectToBackendWithRetry,
	)
}

// -- Messages --
type connMsg *grpc.ClientConn
type dbConnectedMsg struct {
	success bool
	message string
}
type searchResultsMsg []*pb.SearchResult
type statsMsg *pb.DatasetMetadata
type indexStreamMsg struct {
	stream pb.PrismService_IndexClient
	data   *pb.IndexProgress
	err    error
}
type indexDoneMsg struct{}
type openResultMsg string
type licenseActivatedMsg struct {
	success bool
	message string
}
type folderPickedMsg struct {
	success bool
	path    string
	message string
}
type errMsg error
type retryConnectMsg struct{}

// Benchmark messages
type benchmarkProgressMsg struct {
	stream pb.PrismService_RunBenchmarkClient
	data   *pb.BenchmarkProgress
	err    error
}
type benchmarkReportMsg *pb.BenchmarkReport

// -- Commands --
// ... (existing commands same) ...

func pickFolderCmd(client pb.PrismServiceClient) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
		defer cancel()
		resp, err := client.PickFolder(ctx, &pb.PickFolderRequest{Prompt: "Select Dataset Folder"})
		if err != nil {
			return errMsg(err)
		}
		return folderPickedMsg{success: resp.Success, path: resp.Path, message: resp.Message}
	}
}

func connectToBackendWithRetry() tea.Msg {
	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	conn, err := grpc.DialContext(ctx, "localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()), grpc.WithBlock())
	if err != nil {
		return retryConnectMsg{}
	}
	return connMsg(conn)
}

func waitForRetry() tea.Cmd {
	return tea.Tick(1*time.Second, func(_ time.Time) tea.Msg {
		return connectToBackendWithRetry()
	})
}

func getStatsCmd(client pb.PrismServiceClient) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		resp, err := client.GetStats(ctx, &pb.GetStatsRequest{})
		if err != nil {
			return errMsg(err)
		}
		return statsMsg(resp.Metadata)
	}
}

func getSystemInfoCmd(client pb.PrismServiceClient) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		resp, err := client.GetSystemInfo(ctx, &pb.GetSystemInfoRequest{})
		if err != nil {
			return errMsg(err)
		}
		return sysInfoMsg(resp)
	}
}

func connectDBCmd(client pb.PrismServiceClient, path string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		resp, err := client.ConnectDatabase(ctx, &pb.ConnectDatabaseRequest{DbPath: path})
		if err != nil {
			return errMsg(err)
		}
		return dbConnectedMsg{success: resp.Success, message: resp.Message}
	}
}

func activateLicenseCmd(client pb.PrismServiceClient, key string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		resp, err := client.ActivateLicense(ctx, &pb.ActivateLicenseRequest{LicenseKey: key})
		if err != nil {
			return errMsg(err)
		}
		return licenseActivatedMsg{success: resp.Success, message: resp.Message}
	}
}

func searchCmd(client pb.PrismServiceClient, query string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 180*time.Second) // Ultra long timeout for slow model download/load
		defer cancel()
		resp, err := client.Search(ctx, &pb.SearchRequest{QueryText: query})
		if err != nil {
			return errMsg(err)
		}
		return searchResultsMsg(resp.Results)
	}
}

func startIndexCmd(client pb.PrismServiceClient, path string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		stream, err := client.Index(ctx, &pb.IndexRequest{Path: path})
		if err != nil {
			return errMsg(err)
		}
		msg, err := stream.Recv()
		return indexStreamMsg{stream: stream, data: msg, err: err}
	}
}

func nextIndexCmd(stream pb.PrismService_IndexClient) tea.Cmd {
	return func() tea.Msg {
		msg, err := stream.Recv()
		return indexStreamMsg{stream: stream, data: msg, err: err}
	}
}

func openImageCmd(client pb.PrismServiceClient, path string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second) // Increased from 1s to 5s
		defer cancel()
		resp, err := client.OpenResult(ctx, &pb.OpenRequest{FilePath: path})
		if err != nil {
			return errMsg(err)
		}
		if !resp.Success {
			return errMsg(fmt.Errorf("%s", resp.Message))
		}
		return openResultMsg("Opened " + path)
	}
}

// Benchmark Commands
func startBenchmarkCmd(client pb.PrismServiceClient, samplePath string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		stream, err := client.RunBenchmark(ctx, &pb.RunBenchmarkRequest{SamplePath: samplePath})
		if err != nil {
			return errMsg(err)
		}
		msg, err := stream.Recv()
		return benchmarkProgressMsg{stream: stream, data: msg, err: err}
	}
}

func nextBenchmarkCmd(stream pb.PrismService_RunBenchmarkClient) tea.Cmd {
	return func() tea.Msg {
		msg, err := stream.Recv()
		return benchmarkProgressMsg{stream: stream, data: msg, err: err}
	}
}

func getBenchmarkReportCmd(client pb.PrismServiceClient) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		resp, err := client.GetBenchmarkReport(ctx, &pb.GetBenchmarkReportRequest{})
		if err != nil {
			return errMsg(err)
		}
		return benchmarkReportMsg(resp)
	}
}

// -- Update --

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case connMsg:
		m.conn = msg
		m.client = pb.NewPrismServiceClient(m.conn)
		// Don't switch state immediately if we want to show loading animation
		// But for now, let's switch only if loading finishes or we connected
		// Actually, let's keep loading until stats return or timeout
		// For simplicity, we assume connection is the main hurdle.
		// We will switch state in Tick if progress is done, OR if stats return.

		cmds = append(cmds, getStatsCmd(m.client))

	case tickMsg:
		if m.state == stateLoading {
			// Simulate loading progress
			if m.loadingPercent < 1.0 {
				m.loadingPercent += 0.02

				// Simulate logs
				if m.loadingPercent < 0.2 {
					m.loadingLog = "Initializing Prism Daemon..."
				} else if m.loadingPercent < 0.4 {
					m.loadingLog = "Loading Configuration..."
				} else if m.loadingPercent < 0.6 {
					m.loadingLog = "Connecting to Neural Core..."
				} else if m.loadingPercent < 0.8 {
					m.loadingLog = "Verifying Database Integrity..."
				} else {
					m.loadingLog = "Starting Interface..."
				}

				cmds = append(cmds, tickCmd())

				// Update progress bar model
				cmd = m.progress.SetPercent(m.loadingPercent)
				cmds = append(cmds, cmd)
			} else {
				// Loading done, check if we are connected
				if m.client != nil {
					m.state = stateHome
				} else {
					// Still waiting for connection...
					m.loadingLog = "Waiting for Backend Connection..."
					cmds = append(cmds, tickCmd())
				}
			}
		}

	case retryConnectMsg:
		cmds = append(cmds, waitForRetry())

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		}

		if m.state != stateLoading {
			switch msg.String() {
			case "tab":
				// Cycle states: Home -> Search -> Index -> Settings -> Home
				if m.state == stateHome {
					m.state = stateSearch
					m.searchInput.Focus()
				} else if m.state == stateSearch {
					m.state = stateIndex
					m.pathInput.Focus()
				} else if m.state == stateIndex {
					m.state = stateSettings
					m.pathInput.Blur()
					m.loadingSys = true
					cmds = append(cmds, getSystemInfoCmd(m.client))
				} else if m.state == stateSettings {
					m.state = stateHome
				} else if m.state == stateCloudConfig {
					if m.cloudProvider == 0 {
						m.cloudProvider = 1
					} else {
						m.cloudProvider = 0
					}
					m.cloudStatus = "Switched Provider"
				} else {
					m.state = stateHome
					m.dbInput.Blur()
				}

			case "up", "k":
				if m.state == stateHome {
					if m.dashboardCursor > 0 {
						m.dashboardCursor--
					}
					if m.cursor > 0 {
						m.cursor--
					}
				} else if m.state == stateCloudConfig {
					// Handle focus cycle
					if m.cloudProvider == 0 { // AWS
						m.cloudFocusIndex--
						if m.cloudFocusIndex < 0 {
							m.cloudFocusIndex = 2
						}
						// Apply focus
						if m.cloudFocusIndex == 0 {
							m.awsAccessKey.Focus()
							m.awsSecretKey.Blur()
							m.awsRegion.Blur()
						}
						if m.cloudFocusIndex == 1 {
							m.awsAccessKey.Blur()
							m.awsSecretKey.Focus()
							m.awsRegion.Blur()
						}
						if m.cloudFocusIndex == 2 {
							m.awsAccessKey.Blur()
							m.awsSecretKey.Blur()
							m.awsRegion.Focus()
						}
					}
				}

			case "down", "j":
				if m.state == stateHome {
					if m.dashboardCursor < len(m.dashboardOptions)-1 {
						m.dashboardCursor++
					}
				} else if m.state == stateSearch && !m.searchInput.Focused() {
					// Pagination Check: cursor assumes strictly within current page
					// We calculate limit based on page size later, but for cursor movement we just clamp to page size
					// Actually, let's keep cursor relative to the page (0-14)
					if m.cursor < 14 && (m.page*15+m.cursor+1 < len(m.results)) {
						m.cursor++
					}
				} else if m.state == stateCloudConfig {
					if m.cloudProvider == 0 { // AWS
						m.cloudFocusIndex++
						if m.cloudFocusIndex > 2 {
							m.cloudFocusIndex = 0
						}
						// Apply focus
						if m.cloudFocusIndex == 0 {
							m.awsAccessKey.Focus()
							m.awsSecretKey.Blur()
							m.awsRegion.Blur()
						}
						if m.cloudFocusIndex == 1 {
							m.awsAccessKey.Blur()
							m.awsSecretKey.Focus()
							m.awsRegion.Blur()
						}
						if m.cloudFocusIndex == 2 {
							m.awsAccessKey.Blur()
							m.awsSecretKey.Blur()
							m.awsRegion.Focus()
						}
					}
				}

			case "left", "h":
				if m.state == stateSearch && !m.searchInput.Focused() && m.page > 0 {
					m.page--
					m.cursor = 0
				}

			case "right", "l":
				if m.state == stateSearch && !m.searchInput.Focused() {
					pageSize := 15
					if (m.page+1)*pageSize < len(m.results) {
						m.page++
						m.cursor = 0
					}
				}

			case "enter":
				if m.state == stateHome {
					switch m.dashboardOptions[m.dashboardCursor] {
					case "Search Dataset":
						m.state = stateSearch
						m.searchInput.Focus()
					case "Index New Data":
						m.state = stateIndex
						m.pathInput.Focus()
					case "Cloud Ingestion (S3)":
						if m.sysInfo != nil && m.sysInfo.IsPro {
							// Logic for S3
							m.indexStatus = "S3 Ingestion Module Loading..."
						} else {
							m.state = statePro
							m.proStatus = "Cloud Ingestion is a Prism Pro feature."
						}
					case "Connect Database":
						m.state = stateConnectDB
						m.dbInput.Focus()
					case "Upgrade to Pro":
						m.state = statePro
						m.licenseInput.Focus()
					case "Quit":
						return m, tea.Quit
					}
				} else if m.state == statePro {
					if m.licenseInput.Value() != "" && !m.activating {
						m.activating = true
						m.proStatus = "Validating license..."
						cmds = append(cmds, activateLicenseCmd(m.client, m.licenseInput.Value()))
					}
				} else if m.state == stateConnectDB {

					cmds = append(cmds, connectDBCmd(m.client, m.dbInput.Value()))
					m.connecting = true
					m.dbStatus = "Connecting..."
				} else if m.state == stateSearch {
					if !m.searchInput.Focused() && len(m.results) > 0 {
						// Resolve absolute index
						absIdx := m.page*15 + m.cursor
						if absIdx < len(m.results) {
							cmds = append(cmds, openImageCmd(m.client, m.results[absIdx].Path))
						}
					} else {
						m.searchInput.Blur()
						m.results = nil
						m.searching = true
						cmds = append(cmds, searchCmd(m.client, m.searchInput.Value()))
					}
				} else if m.state == stateIndex {
					if !m.indexing {
						m.indexing = true
						m.pathInput.Blur()
						cmds = append(cmds, startIndexCmd(m.client, m.pathInput.Value()))
					}
				} else if m.state == stateCloudConfig && !m.savingCloud {
					// Enter in Cloud Config saves credentials
					m.savingCloud = true
					m.cloudStatus = "Saving..."
					if m.cloudProvider == 0 {
						cmds = append(cmds, saveCloudCredentialsCmd(m.client, "aws", m.awsAccessKey.Value(), m.awsSecretKey.Value(), m.awsRegion.Value(), ""))
					} else {
						cmds = append(cmds, saveCloudCredentialsCmd(m.client, "azure", "", "", "", m.azureConnStr.Value()))
					}
				}

			case "o":
				if m.state == stateIndex && !m.indexing {
					cmds = append(cmds, pickFolderCmd(m.client))
					// Return early to prevent 'o' from being typed into pathInput
					return m, tea.Batch(cmds...)
				}

			case "b":
				if m.state == stateSettings {
					m.state = stateBenchmark
				}

			case "c":
				if m.state == stateSettings {
					m.state = stateCloudConfig
					m.cloudStatus = "" // Reset status
					m.cloudFocusIndex = 0
					// Auto-focus first input
					if m.cloudProvider == 0 {
						m.awsAccessKey.Focus()
					} else {
						m.azureConnStr.Focus()
					}
				}

			case "esc":

				if m.state == stateSearch {
					m.searchInput.Focus()
				}
				if m.state == stateConnectDB {
					m.state = stateHome
					m.dbInput.Blur()
				}
				if m.state == stateIndex {
					m.state = stateHome
					m.pathInput.Blur()
				}
				if m.state == statePro {
					m.state = stateHome
					m.licenseInput.Blur()
				}
				if m.state == stateBenchmark {
					m.state = stateSettings
				}
				if m.state == stateCloudConfig {
					m.state = stateSettings
					m.cloudStatus = "" // clear status
				}

			case "r":

				// Re-run benchmark
				if m.state == stateBenchmark && !m.benchmarking {
					m.benchmarking = true
					m.benchmarkPhase = "starting"
					m.benchmarkProgress = "Initializing..."
					cmds = append(cmds, startBenchmarkCmd(m.client, "data/sample"))
				}

			case "s":
				if m.state == stateCloudConfig && !m.savingCloud && !m.awsAccessKey.Focused() && !m.awsSecretKey.Focused() && !m.awsRegion.Focused() && !m.azureConnStr.Focused() {
					m.savingCloud = true
					m.cloudStatus = "Saving & Connecting..."
					if m.cloudProvider == 0 {
						cmds = append(cmds, saveCloudCredentialsCmd(m.client, "aws", m.awsAccessKey.Value(), m.awsSecretKey.Value(), m.awsRegion.Value(), ""))
					} else {
						cmds = append(cmds, saveCloudCredentialsCmd(m.client, "azure", "", "", "", m.azureConnStr.Value()))
					}
				}

			case "t":
				if m.state == stateCloudConfig && !m.savingCloud && !m.awsAccessKey.Focused() && !m.awsSecretKey.Focused() && !m.awsRegion.Focused() && !m.azureConnStr.Focused() {
					m.savingCloud = true
					m.cloudStatus = "Testing Connection..."
					provider := "aws"
					if m.cloudProvider == 1 {
						provider = "azure"
					}
					cmds = append(cmds, validateCloudCredentialsCmd(m.client, provider))
				}
			}

			// Handle enter in benchmark state
			if m.state == stateBenchmark && msg.String() == "enter" && !m.benchmarking {
				m.benchmarking = true
				m.benchmarkPhase = "starting"
				m.benchmarkProgress = "Initializing..."
				cmds = append(cmds, startBenchmarkCmd(m.client, "data/sample"))
			}
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.progress.Width = msg.Width - 20

	case statsMsg:
		m.loadingStats = false
		m.stats = msg
		// If we got stats, we are definitely connected.
		// If simulated loading is also done, switching to home is handled in Tick.
		// If loading not done, we wait.
		// If loading done but waiting for stats (rare race), we might need to handle.
		// For now, let Tick handle transition to Home when loading is 100% AND client != nil.

	case folderPickedMsg:
		if msg.success {
			m.pathInput.SetValue(msg.path)
		} else if msg.message != "" {
			m.indexStatus = "Picker: " + msg.message
		}

	case licenseActivatedMsg:
		m.activating = false
		m.proStatus = msg.message
		if msg.success {
			cmds = append(cmds, getSystemInfoCmd(m.client))
			m.addNotification(NotifySuccess, "Pro license activated!")
		} else {
			m.addNotification(NotifyError, "License activation failed")
		}

	case sysInfoMsg:
		m.loadingSys = false
		m.sysInfo = msg
		m.devMode = msg.DeveloperMode
		// If Pro, remove "Upgrade to Pro" from menu
		if msg.IsPro {
			newOpts := []string{}
			for _, opt := range m.dashboardOptions {
				if opt != "Upgrade to Pro" {
					newOpts = append(newOpts, opt)
				}
			}
			m.dashboardOptions = newOpts
			if m.dashboardCursor >= len(m.dashboardOptions) {
				m.dashboardCursor = 0
			}
		}

	case dbConnectedMsg:
		m.connecting = false
		if msg.success {
			m.dbStatus = "Connected!"
			m.addNotification(NotifySuccess, "Database connected")
		} else {
			m.dbStatus = msg.message
			m.addNotification(NotifyError, "DB connection failed")
		}

	case cloudSaveMsg:
		m.savingCloud = false
		if msg.success {
			m.cloudStatus = "Success: " + msg.message
			m.addNotification(NotifySuccess, msg.message)
		} else {
			m.cloudStatus = "Error: " + msg.message
			m.addNotification(NotifyError, "Cloud config failed")
		}
		// The following lines seem to be a copy-paste error from the original dbConnectedMsg.
		// They are syntactically incorrect and will be removed to ensure valid Go code.
		// ppend(cmds, getStatsCmd(m.client))
		// m.state = stateHome // Go back to dashboard on success
		// } else {
		// m.dbStatus = "Error: " + msg.message
		// }

	case searchResultsMsg:
		m.searching = false
		m.results = msg
		m.cursor = 0
		m.page = 0
		if len(m.results) > 0 {
			m.searchInput.Blur()
			m.addNotification(NotifyInfo, fmt.Sprintf("Found %d results", len(m.results)))
		} else {
			m.searchInput.Focus()
			m.addNotification(NotifyWarning, "No results found")
		}

	case indexStreamMsg:
		if msg.err == io.EOF {
			m.indexing = false
			m.indexStatus = "Indexing complete!"
			m.pathInput.Focus()
			cmds = append(cmds, m.progress.SetPercent(1.0))
			cmds = append(cmds, getStatsCmd(m.client))
			// Add success notification
			summary := fmt.Sprintf("Indexed %d frames", m.indexCurrent)
			if m.indexSkipped > 0 {
				summary += fmt.Sprintf(" (%d skipped)", m.indexSkipped)
			}
			m.addNotification(NotifySuccess, summary)
		} else if msg.err != nil {
			m.err = msg.err
			m.indexing = false
			m.indexStatus = fmt.Sprintf("Error: %v", msg.err)
			m.addNotification(NotifyError, "Indexing failed")
		} else {
			m.indexCurrent = msg.data.Current
			m.indexTotal = msg.data.Total
			m.indexStatus = msg.data.StatusMessage
			m.indexSkipped = msg.data.Skipped
			m.indexETA = msg.data.EtaSeconds
			pct := 0.0
			if m.indexTotal > 0 {
				pct = float64(m.indexCurrent) / float64(m.indexTotal)
			}
			cmd = m.progress.SetPercent(pct)
			cmds = append(cmds, cmd)
			cmds = append(cmds, nextIndexCmd(msg.stream))
		}

	case benchmarkProgressMsg:
		if msg.err == io.EOF {
			m.benchmarking = false
			m.benchmarkPhase = "complete"
			m.benchmarkProgress = "Benchmark complete!"
			cmds = append(cmds, getBenchmarkReportCmd(m.client))
		} else if msg.err != nil {
			m.err = msg.err
			m.benchmarking = false
			m.benchmarkProgress = fmt.Sprintf("Error: %v", msg.err)
		} else {
			m.benchmarkPhase = msg.data.Phase
			m.benchmarkProgress = msg.data.Message
			cmds = append(cmds, nextBenchmarkCmd(msg.stream))
		}

	case benchmarkReportMsg:
		m.benchmarkReport = msg

	case errMsg:
		m.err = msg
		m.loadingStats = false
		m.connecting = false
		m.searching = false
		m.indexing = false
		m.benchmarking = false
		m.addNotification(NotifyError, fmt.Sprintf("%v", msg))
		if m.state == stateConnectDB {
			m.dbStatus = fmt.Sprintf("Error: %v", msg)
		}
		if m.state == stateIndex {
			m.indexStatus = fmt.Sprintf("Error: %v", msg)
		}
	}

	// Update Inputs
	if m.state == stateSearch {
		m.searchInput, cmd = m.searchInput.Update(msg)
		cmds = append(cmds, cmd)
	}
	if m.state == stateIndex {
		m.pathInput, cmd = m.pathInput.Update(msg)
		cmds = append(cmds, cmd)
	}
	if m.state == stateConnectDB {
		m.dbInput, cmd = m.dbInput.Update(msg)
		cmds = append(cmds, cmd)
	}
	if m.state == statePro {
		m.licenseInput, cmd = m.licenseInput.Update(msg)
		cmds = append(cmds, cmd)
	}
	if m.state == stateCloudConfig {
		// Update cloud inputs
		if m.cloudProvider == 0 {
			m.awsAccessKey, cmd = m.awsAccessKey.Update(msg)
			if cmd != nil {
				cmds = append(cmds, cmd)
			}

			m.awsSecretKey, cmd = m.awsSecretKey.Update(msg)
			if cmd != nil {
				cmds = append(cmds, cmd)
			}

			m.awsRegion, cmd = m.awsRegion.Update(msg)
			if cmd != nil {
				cmds = append(cmds, cmd)
			}
		} else {
			m.azureConnStr, cmd = m.azureConnStr.Update(msg)
			if cmd != nil {
				cmds = append(cmds, cmd)
			}
		}
	}

	// Progress Bar Update
	var progModel tea.Model
	var progCmd tea.Cmd
	progModel, progCmd = m.progress.Update(msg)
	m.progress = progModel.(progress.Model)
	cmds = append(cmds, progCmd)

	m.spinner, cmd = m.spinner.Update(msg)
	cmds = append(cmds, cmd)

	return m, tea.Batch(cmds...)
}

// -- View --

func (m model) View() string {
	if m.state == stateLoading {
		return docStyle.Render(viewLoading(m))
	}

	var doc strings.Builder

	// 1. Header (Tabs)
	tabs := []string{"Dashboard", "Search", "Index", "Settings"}
	var renderedTabs []string
	for i, t := range tabs {
		isActive := false
		if (m.state == stateHome || m.state == stateConnectDB) && i == 0 {
			isActive = true
		} else if m.state == stateSearch && i == 1 {
			isActive = true
		} else if m.state == stateIndex && i == 2 {
			isActive = true
		} else if m.state == stateSettings && i == 3 {
			isActive = true
		}

		if isActive {
			renderedTabs = append(renderedTabs, activeTabStyle.Render(t))
		} else {
			renderedTabs = append(renderedTabs, tabStyle.Render(t))
		}
	}
	tabRow := lipgloss.JoinHorizontal(lipgloss.Bottom, renderedTabs...)
	gap := tabGapStyle.Render(strings.Repeat(" ", max(0, m.width-lipgloss.Width(tabRow)-2)))
	header := lipgloss.JoinHorizontal(lipgloss.Bottom, tabRow, gap)
	doc.WriteString(header + "\n\n")

	// 2. Main Content Area (Split View)
	var mainContent string
	switch m.state {
	case stateHome:
		mainContent = viewDashboard(m)
	case stateSearch:
		mainContent = viewSearch(m)
	case stateIndex:
		mainContent = viewIndex(m)
	case stateConnectDB:
		mainContent = viewConnectDB(m)
	case stateSettings:
		mainContent = viewSettings(m)
	case statePro:
		mainContent = viewPro(m)
	case stateBenchmark:
		mainContent = viewBenchmark(m)
	case stateCloudConfig:
		mainContent = viewCloudConfig(m)
	}

	// Sidebar Content
	sidebar := viewSidebar(m)

	// Combine Main and Sidebar
	splitView := lipgloss.JoinHorizontal(lipgloss.Top,
		lipgloss.NewStyle().Width(m.width-35).Render(mainContent),
		sidebarStyle.Width(30).Height(m.height-12).Render(sidebar),
	)
	doc.WriteString(splitView)

	// 3. Footer / Help Bar
	statusText := "● OFFLINE"
	if m.client != nil {
		statusText = "● ONLINE"
	}
	statusStyle := lipgloss.NewStyle().Foreground(errorColor).Bold(true)
	if m.client != nil {
		statusStyle = lipgloss.NewStyle().Foreground(successColor).Bold(true)
	}

	helpLeft := subtleStyle.Render(" "+asciiTexture) + "\n " + subtleStyle.Render(" TAB: CYCLE • ↑/↓: NAVIGATE • ENTER: SELECT • CTRL+C: QUIT")
	helpRight := "\n" + statusStyle.Render(statusText+"  ")

	footerGap := strings.Repeat(" ", max(0, m.width-lipgloss.Width(helpLeft)-lipgloss.Width(helpRight)-1))
	footer := lipgloss.JoinHorizontal(lipgloss.Bottom, helpLeft, footerGap, helpRight)

	doc.WriteString("\n" + footer)

	return docStyle.Render(doc.String())
}

func viewSidebar(m model) string {
	var sections []string

	// Section 1: System Health
	healthStatus := "Stable"
	if m.client == nil {
		healthStatus = "Disconnected"
	}
	sections = append(sections,
		headerStyle.Render("NEURAL CORE"),
		fmt.Sprintf("Status: %s", healthStatus),
		fmt.Sprintf("Device: %s", "GPU/MPS"),
	)

	// Section 2: Contextual Info
	if m.state == stateSearch && len(m.results) > 0 && m.cursor < len(m.results) {
		selected := m.results[m.cursor]
		sections = append(sections,
			"\n"+headerStyle.Render("SELECTED FRAME"),
			fmt.Sprintf("Match: %.1f%%", selected.Confidence*100),
			fmt.Sprintf("Res: %s", selected.Resolution),
			fmt.Sprintf("Size: %s", selected.FileSize),
		)
		// Show match type
		if selected.MatchType != "" {
			matchType := "Full Image"
			if selected.MatchType == "object_crop" {
				matchType = "Object Crop"
			}
			sections = append(sections, fmt.Sprintf("Type: %s", matchType))
		}
		// Show detected objects
		if len(selected.DetectedObjects) > 0 {
			sections = append(sections, "\n"+headerStyle.Render("DETECTED"))
			for _, obj := range selected.DetectedObjects {
				sections = append(sections, logTextStyle.Render("• "+obj))
			}
		}
	} else if m.stats != nil {
		sections = append(sections,
			"\n"+headerStyle.Render("DATASET STATS"),
			fmt.Sprintf("Frames: %d", m.stats.TotalFrames),
			fmt.Sprintf("Vectors: %d", m.stats.TotalEmbeddings),
		)
	}

	// Section 3: Notifications (dynamic)
	sections = append(sections, "\n"+headerStyle.Render("NOTIFICATIONS"))

	if len(m.notifications) == 0 {
		sections = append(sections, logTextStyle.Render("No notifications"))
	} else {
		// Show last 5 notifications (most recent first)
		start := len(m.notifications) - 5
		if start < 0 {
			start = 0
		}
		for i := len(m.notifications) - 1; i >= start; i-- {
			n := m.notifications[i]
			var style lipgloss.Style
			var icon string
			switch n.Type {
			case NotifySuccess:
				style = lipgloss.NewStyle().Foreground(successColor)
				icon = "✓"
			case NotifyError:
				style = lipgloss.NewStyle().Foreground(errorColor)
				icon = "✗"
			case NotifyWarning:
				style = lipgloss.NewStyle().Foreground(lipgloss.Color("#FFB800"))
				icon = "⚠"
			default:
				style = logTextStyle
				icon = "•"
			}
			timeStr := formatRelativeTime(n.Timestamp)
			msg := n.Message
			if len(msg) > 22 {
				msg = msg[:19] + "..."
			}
			sections = append(sections, style.Render(fmt.Sprintf("%s %s", icon, msg))+" "+subtleStyle.Render(timeStr))
		}
	}

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

// -- Sub-Views --

func viewLoading(m model) string {
	// 50% width progress bar
	m.progress.Width = 40

	content := lipgloss.JoinVertical(
		lipgloss.Center,
		RenderGradientBanner(),
		"\n",
		m.progress.View(),
		logTextStyle.Render(m.loadingLog),
	)

	// Center the content in the window
	return lipgloss.Place(
		m.width, m.height,
		lipgloss.Center, lipgloss.Center,
		loadingBoxStyle.Render(content),
	)
}

func viewSettings(m model) string {
	var content strings.Builder
	content.WriteString(headerBoxStyle.Render("MODULAR NEURAL COMPONENTS") + "\n\n")

	if m.loadingSys {
		content.WriteString("  " + m.spinner.View() + " Querying component hierarchy...")
	} else if m.sysInfo != nil {
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("CORE DEVICE:"), keywordStyle.Render(m.sysInfo.Device)))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("TRANSFORMER:"), m.sysInfo.SiglipModel))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("DETECTOR:"), m.sysInfo.YoloModel))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("VERSION:"), m.sysInfo.BackendVersion))
		content.WriteString(fmt.Sprintf("%s %d threads\n", statLabelStyle.Render("THREADS:"), m.sysInfo.CpuCount))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("MEMORY:"), m.sysInfo.MemoryUsage))
	} else {
		content.WriteString(subtleStyle.Render("Component telemetry unavailable."))
	}

	// License Status Section
	content.WriteString("\n\n" + headerBoxStyle.Render("LICENSE STATUS") + "\n\n")
	if m.sysInfo != nil && m.sysInfo.IsPro {
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("TIER:"), successStyle.Render("PRO")))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("STATUS:"), successStyle.Render("ACTIVE")))
		if m.sysInfo.LicenseEmail != "" {
			content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("ACCOUNT:"), m.sysInfo.LicenseEmail))
		}
		if m.sysInfo.LicenseExpires != "" {
			content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("EXPIRES:"), m.sysInfo.LicenseExpires))
		}
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("LIMITS:"), "Unlimited Indexing"))
	} else {
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("TIER:"), subtleStyle.Render("Community Edition")))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("STATUS:"), successStyle.Render("All Features Unlocked")))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("LIMITS:"), "Unlimited indexing"))
	}

	// Advanced Section
	content.WriteString("\n\n" + headerBoxStyle.Render("ADVANCED") + "\n\n")
	content.WriteString("  " + keywordStyle.Render("[b]") + " Benchmarks & Diagnostics\n")
	content.WriteString("  " + keywordStyle.Render("[c]") + " Configure Cloud Credentials (Pro)\n")
	content.WriteString(subtleStyle.Render("  Press 'b' or 'c' to access tools\n"))

	return lipgloss.NewStyle().Padding(1, 2).Render(content.String())
}

func viewBenchmark(m model) string {
	var content strings.Builder
	content.WriteString(headerBoxStyle.Render("BENCHMARKS & DIAGNOSTICS") + "\n\n")

	if m.benchmarking {
		content.WriteString(fmt.Sprintf("  %s Running benchmark...\n\n", m.spinner.View()))
		content.WriteString(fmt.Sprintf("  %s %s\n", statLabelStyle.Render("PHASE:"), keywordStyle.Render(m.benchmarkPhase)))
		content.WriteString(fmt.Sprintf("  %s %s\n", statLabelStyle.Render("STATUS:"), m.benchmarkProgress))
	} else if m.benchmarkReport != nil && m.benchmarkReport.Timestamp != "" {
		// Display last report
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("TIMESTAMP:"), m.benchmarkReport.Timestamp))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("DEVICE:"), keywordStyle.Render(m.benchmarkReport.Device)))
		content.WriteString(fmt.Sprintf("%s %s\n", statLabelStyle.Render("OS:"), m.benchmarkReport.Os))
		content.WriteString(fmt.Sprintf("%s %s\n\n", statLabelStyle.Render("VERSION:"), m.benchmarkReport.PrismVersion))

		// Indexing Metrics
		content.WriteString(headerStyle.Render("INDEXING METRICS") + "\n")
		for _, metric := range m.benchmarkReport.IndexingMetrics {
			content.WriteString(fmt.Sprintf("  %s: %.2f %s\n", metric.Name, metric.Value, metric.Unit))
		}

		// Search Metrics
		content.WriteString("\n" + headerStyle.Render("SEARCH METRICS") + "\n")
		for _, metric := range m.benchmarkReport.SearchMetrics {
			content.WriteString(fmt.Sprintf("  %s: %.2f %s\n", metric.Name, metric.Value, metric.Unit))
		}

		// System Metrics
		content.WriteString("\n" + headerStyle.Render("SYSTEM METRICS") + "\n")
		for _, metric := range m.benchmarkReport.SystemMetrics {
			content.WriteString(fmt.Sprintf("  %s: %.2f %s\n", metric.Name, metric.Value, metric.Unit))
		}

		content.WriteString("\n" + subtleStyle.Render("Press 'r' to run again, 'e' to export, ESC to go back"))
	} else {
		content.WriteString(subtleStyle.Render("No benchmark results yet.") + "\n\n")
		content.WriteString("Press " + keywordStyle.Render("ENTER") + " to run a benchmark on sample data.\n")
		content.WriteString(subtleStyle.Render("This will index data/sample and run standard queries.\n"))
		content.WriteString("\n" + subtleStyle.Render("Press ESC to go back"))
	}

	return lipgloss.NewStyle().Padding(1, 2).Render(content.String())
}

func viewDashboard(m model) string {
	// Top: Banner
	banner := RenderGradientBanner()

	// Content Area
	var content strings.Builder
	content.WriteString(headerBoxStyle.Render("SYSTEM OVERVIEW") + "\n\n")

	if m.loadingStats {
		content.WriteString(m.spinner.View() + " Synchronizing with Neural Database...")
	} else if m.stats != nil {
		content.WriteString(fmt.Sprintf(
			"The %s engine is currently monitoring %s frames with a total of %s multidimensional embeddings.\n\n",
			keywordStyle.Render("Prism Neural Core"),
			statValueStyle.Render(fmt.Sprintf("%d", m.stats.TotalFrames)),
			statValueStyle.Render(fmt.Sprintf("%d", m.stats.TotalEmbeddings)),
		))
		content.WriteString(fmt.Sprintf("Active Database: %s\n", keywordStyle.Render(m.stats.DbPath)))
		content.WriteString(fmt.Sprintf("Last Ingestion Trace: %s\n", subtleStyle.Render(m.stats.LastIndexed)))
	} else {
		content.WriteString(subtleStyle.Render("No active intelligence trace detected. Please connect a database."))
	}

	// Menu
	content.WriteString("\n\n" + headerBoxStyle.Render("COMMAND MODULES") + "\n")
	for i, opt := range m.dashboardOptions {
		cursor := "  "
		style := subtleStyle
		if i == m.dashboardCursor {
			cursor = "❯ "
			style = selectedItemStyle
		}
		content.WriteString(style.Render(cursor+opt) + "\n")
	}

	return lipgloss.JoinVertical(lipgloss.Center,
		banner,
		"\n",
		lipgloss.NewStyle().Padding(1, 2).Render(content.String()),
	)
}

func viewSearch(m model) string {
	// Header Section
	header := lipgloss.JoinVertical(lipgloss.Left,
		headerBoxStyle.Render("NEURAL SEARCH INTERFACE")+" "+subtleStyle.Render("v1.0"),
		m.searchInput.View(),
		separatorStyle.Render(strings.Repeat("─", m.width-40)),
	)

	var content string
	if m.searching {
		content = "\n  " + m.spinner.View() + " Reconstructing visual topology..."
	} else if m.err != nil {
		content = lipgloss.NewStyle().Padding(2).Render(
			lipgloss.JoinVertical(lipgloss.Left,
				lipgloss.NewStyle().Foreground(errorColor).Bold(true).Render("!! CORE EXCEPTION !!"),
				"",
				m.err.Error(),
			),
		)
	} else if len(m.results) == 0 {
		content = "\n  " + subtleStyle.Render("Standing by for input. Models lazy-loaded on request.")
	} else {
		var rows []string

		pageSize := 15
		start := m.page * pageSize
		end := start + pageSize
		if end > len(m.results) {
			end = len(m.results)
		}

		// Ensure start is valid (if results shrank drastically, though search resets page)
		if start > len(m.results) {
			start = len(m.results)
		}

		pageResults := m.results[start:end]

		for i, res := range pageResults {
			style := resultPathStyle
			prefix := "  "
			if i == m.cursor {
				style = selectedResultStyle
				prefix = "❯ "
			}

			path := res.Path
			if len(path) > 40 {
				path = "..." + path[len(path)-37:]
			}

			line := fmt.Sprintf("%-42s %s", path, resultScoreStyle.Render(fmt.Sprintf("%d%%", int(res.Confidence*100))))
			rows = append(rows, style.Render(prefix+line))
		}
		content = lipgloss.JoinVertical(lipgloss.Left, rows...)

		// Pagination Footer
		totalPages := (len(m.results) + pageSize - 1) / pageSize
		if totalPages > 1 {
			footer := fmt.Sprintf("\n Page %d/%d (←/→)", m.page+1, totalPages)
			content = lipgloss.JoinVertical(lipgloss.Left, content, subtleStyle.Render(footer))
		}
	}

	return lipgloss.JoinVertical(lipgloss.Left,
		header,
		lipgloss.NewStyle().Height(m.height-18).Render(content),
	)
}

func viewIndex(m model) string {
	header := lipgloss.JoinVertical(lipgloss.Left,
		headerBoxStyle.Render("DATASET INGESTION PIPELINE"),
		"Target Path: "+subtleStyle.Render("(Press 'o' to open folder picker)"),
		m.pathInput.View(),
		separatorStyle.Render(strings.Repeat("─", m.width-40)),
	)

	var status string
	if m.indexing {
		m.progress.Width = m.width - 45

		// Calculate percentage
		pct := 0.0
		if m.indexTotal > 0 {
			pct = float64(m.indexCurrent) / float64(m.indexTotal) * 100
		}

		// Format ETA
		etaStr := "Calculating..."
		if m.indexETA > 0 {
			mins := m.indexETA / 60
			secs := m.indexETA % 60
			if mins > 0 {
				etaStr = fmt.Sprintf("%dm %ds remaining", mins, secs)
			} else {
				etaStr = fmt.Sprintf("%ds remaining", secs)
			}
		} else if m.indexCurrent > 0 && m.indexCurrent == m.indexTotal {
			etaStr = "Complete!"
		}

		// Build status lines
		var statusLines []string
		statusLines = append(statusLines, "\n"+keywordStyle.Render("INGESTION ACTIVE"))
		statusLines = append(statusLines, m.progress.View())
		statusLines = append(statusLines, "")

		// Progress stats line
		statsLine := fmt.Sprintf("  Processed: %d / %d (%.1f%%)", m.indexCurrent, m.indexTotal, pct)
		if m.indexSkipped > 0 {
			statsLine += fmt.Sprintf("  │  Skipped: %d", m.indexSkipped)
		}
		statusLines = append(statusLines, statsLine)

		// ETA line
		statusLines = append(statusLines, subtleStyle.Render("  ETA: "+etaStr))
		statusLines = append(statusLines, "")

		// Current operation
		statusLines = append(statusLines, keywordStyle.Render("  STATUS"))
		statusLines = append(statusLines, "  "+logTextStyle.Render(m.indexStatus))

		status = lipgloss.JoinVertical(lipgloss.Left, statusLines...)
	} else {
		// Not indexing - show instructions
		var lines []string
		lines = append(lines, "")
		if m.indexStatus != "" {
			lines = append(lines, successStyle.Render("  "+m.indexStatus))
		} else {
			lines = append(lines, subtleStyle.Render("  Enter a path or press 'o' to select a folder"))
		}
		lines = append(lines, "")
		lines = append(lines, subtleStyle.Render("  Press ENTER to start indexing"))
		status = lipgloss.JoinVertical(lipgloss.Left, lines...)
	}

	return lipgloss.JoinVertical(lipgloss.Left,
		header,
		status,
	)
}

func viewConnectDB(m model) string {
	content := lipgloss.JoinVertical(lipgloss.Left,
		headerStyle.Render("CONNECT DATABASE"),
		"",
		"SQLite DB Path:",
		m.dbInput.View(),
		"",
		m.spinner.View()+" "+m.dbStatus,
	)

	return lipgloss.Place(m.width, m.height/2, lipgloss.Center, lipgloss.Center, panelStyle.Render(content))
}

func viewPro(m model) string {
	var content strings.Builder
	content.WriteString(headerBoxStyle.Render("🔮 SECRET FEATURES") + "\n\n")

	if m.sysInfo != nil && m.sysInfo.IsPro {
		content.WriteString(successStyle.Render("✔ Secret Features Unlocked!") + "\n\n")
		content.WriteString("You've discovered the hidden features:\n")
		content.WriteString("• 🎨 Custom themes (coming soon)\n")
		content.WriteString("• 🚀 Experimental neural modes\n")
		content.WriteString("• 🔬 Advanced debugging tools\n")
		content.WriteString("• ⚡ Early access to new features\n")
		content.WriteString("\n" + subtleStyle.Render("Press ESC to return"))
	} else {
		content.WriteString("You found a hidden area...\n\n")
		content.WriteString(keywordStyle.Render("ENTER SECRET CODE:") + "\n")
		content.WriteString(m.licenseInput.View() + "\n\n")

		if m.activating {
			content.WriteString(m.spinner.View() + " " + m.proStatus)
		} else if m.proStatus != "" {
			if strings.Contains(m.proStatus, "Activated") || strings.Contains(m.proStatus, "success") {
				content.WriteString(successStyle.Render("✨ " + m.proStatus))
			} else {
				content.WriteString(errorStyle.Render(m.proStatus))
			}
		} else {
			content.WriteString(subtleStyle.Render("Press ENTER to unlock"))
		}

		content.WriteString("\n\n" + subtleStyle.Render("Don't have a key? Visit prism.dev/upgrade"))
		content.WriteString("\n" + subtleStyle.Render("Press ESC to return to dashboard"))
	}

	return lipgloss.NewStyle().Padding(1, 2).Render(content.String())
}

// addNotification adds a notification to the model (keeps last 10)
func (m *model) addNotification(ntype NotificationType, message string) {
	n := Notification{
		Type:      ntype,
		Message:   message,
		Timestamp: time.Now(),
	}
	m.notifications = append(m.notifications, n)
	// Keep only last 10
	if len(m.notifications) > 10 {
		m.notifications = m.notifications[len(m.notifications)-10:]
	}
}

// formatRelativeTime returns a human-readable relative time string
func formatRelativeTime(t time.Time) string {
	diff := time.Since(t)
	if diff < time.Minute {
		return fmt.Sprintf("%ds ago", int(diff.Seconds()))
	} else if diff < time.Hour {
		return fmt.Sprintf("%dm ago", int(diff.Minutes()))
	} else if diff < 24*time.Hour {
		return fmt.Sprintf("%dh ago", int(diff.Hours()))
	}
	return t.Format("Jan 2")
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func viewCloudConfig(m model) string {
	var content strings.Builder

	content.WriteString(headerBoxStyle.Render("CONFIGURE CLOUD CREDENTIALS") + "\n\n")

	// Tabs
	awsTab := " AWS S3 "
	azureTab := " Azure Blob "

	if m.cloudProvider == 0 {
		awsTab = activeTabStyle.Render(awsTab)
		azureTab = tabStyle.Render(azureTab)
	} else {
		awsTab = tabStyle.Render(awsTab)
		azureTab = activeTabStyle.Render(azureTab)
	}

	content.WriteString(awsTab + "  " + azureTab + "\n\n")
	content.WriteString(subtleStyle.Render("Press TAB to switch providers.") + "\n\n")

	if m.cloudProvider == 0 {
		content.WriteString("Access Key ID:\n")
		content.WriteString(m.awsAccessKey.View() + "\n\n")

		content.WriteString("Secret Access Key:\n")
		content.WriteString(m.awsSecretKey.View() + "\n\n")

		content.WriteString("Region:\n")
		content.WriteString(m.awsRegion.View() + "\n\n")
	} else {
		content.WriteString("Connection String:\n")
		content.WriteString(m.azureConnStr.View() + "\n\n")
	}

	content.WriteString("\n")
	content.WriteString("  " + keywordStyle.Render("[↑/↓]") + " Navigate fields\n")
	content.WriteString("  " + keywordStyle.Render("[ENTER]") + " Save Credentials\n")
	content.WriteString("  " + keywordStyle.Render("[T]") + " Test Connection\n")
	content.WriteString("  " + keywordStyle.Render("[TAB]") + " Switch Provider\n")
	content.WriteString("  " + keywordStyle.Render("[ESC]") + " Back\n")

	if m.cloudStatus != "" {
		content.WriteString("\nStatus: " + m.cloudStatus + "\n")
	}

	return lipgloss.NewStyle().Padding(1, 2).Render(content.String())
}

type cloudSaveMsg struct {
	success bool
	message string
}

func saveCloudCredentialsCmd(client pb.PrismServiceClient, provider, awsKey, awsSecret, awsRegion, azConn string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		resp, err := client.SaveCloudCredentials(ctx, &pb.SaveCloudCredentialsRequest{
			Provider:              provider,
			AwsAccessKey:          awsKey,
			AwsSecretKey:          awsSecret,
			AwsRegion:             awsRegion,
			AzureConnectionString: azConn,
		})

		if err != nil {
			return cloudSaveMsg{success: false, message: err.Error()}
		}
		if resp == nil {
			return cloudSaveMsg{success: false, message: "Empty response from server"}
		}
		return cloudSaveMsg{success: resp.Success, message: resp.Message}
	}
}

func validateCloudCredentialsCmd(client pb.PrismServiceClient, provider string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		resp, err := client.ValidateCloudCredentials(ctx, &pb.ValidateCloudCredentialsRequest{
			Provider: provider,
		})

		if err != nil {
			return cloudSaveMsg{success: false, message: err.Error()}
		}
		if resp == nil {
			return cloudSaveMsg{success: false, message: "Empty response from server"}
		}
		return cloudSaveMsg{success: resp.Success, message: resp.Message}
	}
}

func main() {
	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		log.Fatal(err)
	}
}
