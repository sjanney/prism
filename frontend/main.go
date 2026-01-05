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
)

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

	sp := spinner.New()
	sp.Spinner = spinner.Dot
	sp.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	return model{
		state:            stateLoading,
		dashboardOptions: []string{"Search Dataset", "Index New Data", "Cloud Ingestion (S3)", "Connect Database", "Upgrade to Pro", "Quit"},
		dashboardCursor:  0,
		searchInput:      si,
		pathInput:        pi,
		dbInput:          di,

		progress:       prog,
		spinner:        sp,
		loadingStats:   true,
		loadingPercent: 0.0,
		loadingLog:     "Initializing system...",

		licenseInput: func() textinput.Model {
			li := textinput.New()
			li.Placeholder = "PRISM-PRO-XXXX-XXXX"
			li.CharLimit = 32
			li.Width = 40
			return li
		}(),
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
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second) // Long timeout for model cold start
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
		ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
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
				} else {
					m.state = stateHome
					m.dbInput.Blur()
				}

			case "up", "k":
				if m.state == stateHome {
					if m.dashboardCursor > 0 {
						m.dashboardCursor--
					}
				} else if m.state == stateSearch && !m.searchInput.Focused() {
					if m.cursor > 0 {
						m.cursor--
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
					// Placeholder: Do nothing or return to home?
					// m.activating = true
					// m.proStatus = "Activating..."
					// cmds = append(cmds, activateLicenseCmd(m.client, m.licenseInput.Value()))
					m.state = stateHome
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
				}

			case "o":
				if m.state == stateIndex && !m.indexing {
					cmds = append(cmds, pickFolderCmd(m.client))
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
			// Refresh dashboard options in next step or via sysInfo
		}

	case sysInfoMsg:
		m.loadingSys = false
		m.sysInfo = msg
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
			cmds = append(cmds, getStatsCmd(m.client))
			m.state = stateHome // Go back to dashboard on success
		} else {
			m.dbStatus = "Error: " + msg.message
		}

	case searchResultsMsg:
		m.searching = false
		m.results = msg
		m.cursor = 0
		m.page = 0
		if len(m.results) > 0 {
			m.searchInput.Blur()
		} else {
			m.searchInput.Focus()
		}

	case indexStreamMsg:
		if msg.err == io.EOF {
			m.indexing = false
			m.indexStatus = "Indexing complete!"
			m.pathInput.Focus()
			cmds = append(cmds, m.progress.SetPercent(1.0))
			cmds = append(cmds, getStatsCmd(m.client))
		} else if msg.err != nil {
			m.err = msg.err
			m.indexing = false
			m.indexStatus = fmt.Sprintf("Error: %v", msg.err)
		} else {
			m.indexCurrent = msg.data.Current
			m.indexTotal = msg.data.Total
			m.indexStatus = msg.data.StatusMessage // "Processing file..."
			pct := 0.0
			if m.indexTotal > 0 {
				pct = float64(m.indexCurrent) / float64(m.indexTotal)
			}
			cmd = m.progress.SetPercent(pct)
			cmds = append(cmds, cmd)
			cmds = append(cmds, nextIndexCmd(msg.stream))
		}

	case errMsg:
		m.err = msg
		m.loadingStats = false
		m.connecting = false
		m.searching = false
		m.indexing = false
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
	if m.state == stateSearch && len(m.results) > 0 {
		selected := m.results[m.cursor]
		sections = append(sections,
			"\n"+headerStyle.Render("SELECTED FRAME"),
			fmt.Sprintf("Match: %.1f%%", selected.Confidence*100),
			fmt.Sprintf("Res: %s", selected.Resolution),
			fmt.Sprintf("Size: %s", selected.FileSize),
		)
	} else if m.stats != nil {
		sections = append(sections,
			"\n"+headerStyle.Render("DATASET STATS"),
			fmt.Sprintf("Frames: %d", m.stats.TotalFrames),
			fmt.Sprintf("Vectors: %d", m.stats.TotalEmbeddings),
		)
	}

	// Section 3: Recent Logs (Simulation/Real)
	sections = append(sections,
		"\n"+headerStyle.Render("ACTIVITY LOG"),
		logTextStyle.Render("Interface Ready"),
		logTextStyle.Render("Backend Synced"),
	)

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
		headerBoxStyle.Render("NEURAL SEARCH INTERFACE")+" "+subtleStyle.Render("v2.3"),
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
		status = lipgloss.JoinVertical(lipgloss.Left,
			"\n"+keywordStyle.Render("INGESTION ACTIVE"),
			m.progress.View(),
			logTextStyle.Render(m.indexStatus),
			"",
			fmt.Sprintf("Trace: %d / %d processed", m.indexCurrent, m.indexTotal),
		)
	} else {
		status = "\n" + subtleStyle.Render(m.indexStatus)
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
	content.WriteString(headerBoxStyle.Render("PRISM PRO ACTIVATION") + "\n\n")

	if m.sysInfo != nil && m.sysInfo.IsPro {
		content.WriteString(successStyle.Render("✔ Prism Pro is Active") + "\n\n")
		content.WriteString("Thank you for supporting Prism! You have unlocked:\n")
		content.WriteString("• Unlimited local indexing\n")
		content.WriteString("• Advanced S3 Ingestion (COMING SOON)\n")
		content.WriteString("• Priority Neural Core Support\n")
	} else {
		content.WriteString("Unlock the full potential of your AV data.\n\n")
		content.WriteString(keywordStyle.Render("PRO FEATURES COMING SOON!") + "\n\n")
		content.WriteString("We are working hard to bring you:\n")
		content.WriteString("• Unlimited local indexing\n")
		content.WriteString("• Cloud Ingestion (S3)\n\n")

		content.WriteString(subtleStyle.Render("Check back later for availability."))

		// Disable Input View
		// content.WriteString("Enter License Key:\n")
		// content.WriteString(m.licenseInput.View() + "\n\n")

		// if m.activating {
		// 	content.WriteString(m.spinner.View() + " " + m.proStatus)
		// } else {
		// 	content.WriteString(subtleStyle.Render(m.proStatus))
		// }

		// content.WriteString("\n\n" + subtleStyle.Render("Don't have a key? Visit prism.dev/upgrade"))
	}

	return lipgloss.NewStyle().Padding(1, 2).Render(content.String())
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func main() {
	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		log.Fatal(err)
	}
}
