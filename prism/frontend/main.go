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
	"github.com/charmbracelet/bubbletea"
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
)

type sysInfoMsg *pb.GetSystemInfoResponse

// Main Model
type model struct {
	client     pb.PrismServiceClient
	conn       *grpc.ClientConn
	state      state
	err        error
	width      int
	height     int

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
	searching   bool

	// Global Spinner
	spinner      spinner.Model

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
	sysInfo      *pb.GetSystemInfoResponse
	loadingSys   bool
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
		dashboardOptions: []string{"Search Dataset", "Index New Data", "Connect Database", "Quit"},
		dashboardCursor:  0,
		searchInput:      si,
		pathInput:        pi,
		dbInput:          di,

		progress:     prog,
		spinner:      sp,
		loadingStats: true,
		loadingPercent: 0.0,
		loadingLog:     "Initializing system...",
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
type errMsg error
type retryConnectMsg struct{}

// -- Commands --
// ... (existing commands same) ...

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

func searchCmd(client pb.PrismServiceClient, query string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
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
			return errMsg(fmt.Errorf(resp.Message))
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
					if m.cursor < len(m.results)-1 {
						m.cursor++
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
					case "Connect Database":
						m.state = stateConnectDB
						m.dbInput.Focus()
					case "Quit":
						return m, tea.Quit
					}
				} else if m.state == stateConnectDB {
					cmds = append(cmds, connectDBCmd(m.client, m.dbInput.Value()))
					m.connecting = true
					m.dbStatus = "Connecting..."
				} else if m.state == stateSearch {
					if !m.searchInput.Focused() && len(m.results) > 0 {
						cmds = append(cmds, openImageCmd(m.client, m.results[m.cursor].Path))
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
        
	case sysInfoMsg:
		m.loadingSys = false
		m.sysInfo = msg
        
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
	var doc strings.Builder

	// 1. Header (Tabs)
    if m.state != stateLoading {
        tabs := []string{"Dashboard", "Search", "Index", "Settings"}
        var renderedTabs []string
        for i, t := range tabs {
            isActive := false
            if (m.state == stateHome || m.state == stateConnectDB) && i == 0 {
                isActive = true
            }
            if m.state == stateSearch && i == 1 {
                isActive = true
            }
            if m.state == stateIndex && i == 2 {
                isActive = true
            }
            if m.state == stateSettings && i == 3 {
                isActive = true
            }

            if isActive {
                renderedTabs = append(renderedTabs, activeTabStyle.Render(t))
            } else {
                renderedTabs = append(renderedTabs, tabStyle.Render(t))
            }
        }
        row := lipgloss.JoinHorizontal(lipgloss.Bottom, renderedTabs...)
        gap := tabGapStyle.Render(strings.Repeat(" ", max(0, m.width-lipgloss.Width(row)-2)))
        header := lipgloss.JoinHorizontal(lipgloss.Bottom, row, gap)
        doc.WriteString(header + "\n\n")
    }

	// 2. Main Content Area
	switch m.state {
	case stateLoading:
		doc.WriteString(viewLoading(m))
	case stateHome:
		doc.WriteString(viewDashboard(m))
	case stateSearch:
		doc.WriteString(viewSearch(m))
	case stateIndex:
		doc.WriteString(viewIndex(m))
	case stateConnectDB:
		doc.WriteString(viewConnectDB(m))
	case stateSettings:
		doc.WriteString(viewSettings(m))
	}

	// 3. Footer
    if m.state != stateLoading {
        statusText := "● OFFLINE"
        if m.client != nil {
            statusText = "● ONLINE"
        }
        
        statusStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FF3333")).Bold(true)
        if m.client != nil {
            statusStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00")).Bold(true)
        }

        left := subtleStyle.Render("PRISM v2.3 • Tab: Switch • Ctrl+C: Quit")
        right := statusStyle.Render(statusText)
        
        gap := strings.Repeat(" ", max(0, m.width-lipgloss.Width(left)-lipgloss.Width(right)-2))
        doc.WriteString("\n\n" + left + gap + right)
    }

	return docStyle.Render(doc.String())
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
	var content string
	if m.loadingSys {
		content = m.spinner.View() + " Querying Neural Core Components..."
	} else if m.sysInfo != nil {
		content = fmt.Sprintf(
			"%s\n%s\n\n%s\n%s\n\n%s\n%s\n\n%s\n%s\n\n%s\n%s\n\n%s\n%s",
			statLabelStyle.Render("Inference Device"), statValueStyle.Render(m.sysInfo.Device),
			statLabelStyle.Render("Vision Model"), statValueStyle.Render(m.sysInfo.SiglipModel),
			statLabelStyle.Render("Detection Model"), statValueStyle.Render(m.sysInfo.YoloModel),
			statLabelStyle.Render("Backend Logic"), statValueStyle.Render(m.sysInfo.BackendVersion),
			statLabelStyle.Render("Compute Threads"), statValueStyle.Render(fmt.Sprintf("%d", m.sysInfo.CpuCount)),
			statLabelStyle.Render("System Memory"), statValueStyle.Render(m.sysInfo.MemoryUsage),
		)
	} else {
		content = subtleStyle.Render("System telemetry unavailable.")
	}

	panel := panelStyle.
		Width(m.width - 20).
		Height(m.height - 15).
		Render(
			lipgloss.JoinVertical(lipgloss.Left,
				headerStyle.Render("SYSTEM CONFIGURATION & MODULAR CORE"),
				"",
				content,
			),
		)

	return lipgloss.Place(m.width, m.height-10, lipgloss.Center, lipgloss.Top, panel)
}

func viewDashboard(m model) string {
	// Top: Banner
	banner := RenderGradientBanner()

	// Middle: Two Columns
	// Left: Stats Panel
	var statsContent string
	if m.loadingStats {
		statsContent = m.spinner.View() + " Fetching Telemetry..."
	} else if m.stats != nil {
		statsContent = fmt.Sprintf(
			"%s\n%s\n\n%s\n%s\n\n%s\n%s\n\n%s\n%s",
			statLabelStyle.Render("Frames Processed"), statValueStyle.Render(fmt.Sprintf("%d", m.stats.TotalFrames)),
			statLabelStyle.Render("Vector Embeddings"), statValueStyle.Render(fmt.Sprintf("%d", m.stats.TotalEmbeddings)),
			statLabelStyle.Render("Active DB"), statValueStyle.Render(m.stats.DbPath),
			statLabelStyle.Render("Last Update"), statValueStyle.Render(m.stats.LastIndexed),
		)
	} else {
		statsContent = subtleStyle.Render("No Data Available.\nConnect a Database.")
	}
	statsPanel := panelStyle.
		Width(40).
		Height(12).
		Render(
			lipgloss.JoinVertical(lipgloss.Left,
				headerStyle.Render("SYSTEM TELEMETRY"),
				"",
				statsContent,
			),
		)

	// Right: Menu/Actions
	var options []string
	for i, opt := range m.dashboardOptions {
		cursor := "  "
		style := subtleStyle
		if i == m.dashboardCursor {
			cursor = "> "
			style = selectedItemStyle
		}
		options = append(options, style.Render(cursor+opt))
	}
	menuPanel := panelStyle.
		Width(30).
		Height(12).
		Render(
			lipgloss.JoinVertical(lipgloss.Left,
				headerStyle.Render("CONTROL CENTER"),
				"",
				lipgloss.JoinVertical(lipgloss.Left, options...),
			),
		)

	return lipgloss.JoinVertical(
		lipgloss.Center,
		banner,
		lipgloss.JoinHorizontal(lipgloss.Top, statsPanel, "   ", menuPanel),
	)
}

func viewSearch(m model) string {
	// Input Area
	input := panelStyle.Render(
		lipgloss.JoinVertical(lipgloss.Left,
			headerStyle.Render("NATURAL LANGUAGE QUERY"),
			m.searchInput.View(),
		),
	)

	// Split View: Results List (Left) | Detail Panel (Right)
	var content string
	
	if m.searching {
		content = m.spinner.View() + " Accessing Neural Index..."
	} else if m.err != nil {
		content = lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Foreground(lipgloss.Color("#FF3333")).Render("SEARCH ERROR"),
			"",
			m.err.Error(),
			"",
			subtleStyle.Render("Note: If you recently upgraded models, you may need to re-index."),
		)
	} else if len(m.results) == 0 {
		content = subtleStyle.Render("Enter a query to search the visual dataset.\nModels will lazy-load on first search.")
	} else {
		// 1. Result List
		var rows []string
		for i, res := range m.results {
			style := resultPathStyle
			prefix := "  "
			if i == m.cursor {
				style = selectedResultStyle
				prefix = "> "
			}
			// Truncate path for list view
			shortPath := res.Path
			if len(shortPath) > 50 {
				shortPath = "..." + shortPath[len(shortPath)-47:]
			}
			
			line := fmt.Sprintf("%s%s %s", prefix, shortPath, resultScoreStyle.Render(fmt.Sprintf("(%.1f%%)", res.Confidence*100)))
			rows = append(rows, style.Render(line))
		}
		listParams := lipgloss.NewStyle().Width(55).Height(m.height - 18) // Scrollable logically if we had a viewport, simpler for now
		listPanel := listParams.Render(lipgloss.JoinVertical(lipgloss.Left, rows...))

		// 2. Detail Panel (for selected item)
		var detailPanel string
		if len(m.results) > 0 {
			selected := m.results[m.cursor]
			
			// Metadata Table
			meta := fmt.Sprintf(
				"Resolution:  %s\nFile Size:   %s\nModified:    %s\nReasoning:   %s",
				selected.Resolution,
				selected.FileSize,
				selected.DateModified,
				selected.Reasoning,
			)
			
			detailPanel = lipgloss.JoinVertical(lipgloss.Left,
				headerStyle.Render("IMAGE INTELLIGENCE"),
				"",
				lipgloss.NewStyle().Foreground(secondaryColor).Bold(true).Render(selected.Path),
				"",
				panelStyle.Render(meta),
				"",
				subtleStyle.Render("Press Enter to Open"),
			)
		}

		content = lipgloss.JoinHorizontal(lipgloss.Top, 
			listPanel, 
			panelStyle.PaddingLeft(2).Render(detailPanel),
		)
	}

	resultsPanel := panelStyle.
		Width(m.width - 10).
		Height(m.height - 15).
		Render(content)

	return lipgloss.JoinVertical(lipgloss.Left, input, resultsPanel)
}

func viewIndex(m model) string {
	input := panelStyle.Render(
		lipgloss.JoinVertical(lipgloss.Left,
			headerStyle.Render("DATASET INGESTION"),
			"Target Directory:",
			m.pathInput.View(),
		),
	)

	var status string
	if m.indexing {
        m.progress.Width = m.width - 20
		status = lipgloss.JoinVertical(lipgloss.Left,
			m.progress.View(),
			logTextStyle.Render(m.indexStatus), // Use tiny info log style here too
            "",
			fmt.Sprintf("Processing: %d / %d", m.indexCurrent, m.indexTotal),
		)
	} else {
		status = subtleStyle.Render(m.indexStatus)
	}

	statusPanel := panelStyle.
		Width(m.width - 10).
		Height(10).
		Render(status)

	return lipgloss.JoinVertical(lipgloss.Left, input, statusPanel)
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
