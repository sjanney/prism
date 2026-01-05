package main

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/lucasb-eyer/go-colorful"
)

var (
	// -- Colors --
	// A "Cyberpunk/Premium" palette
	primaryColor   = lipgloss.Color("#9D46FF") // Lighter Electric Purple (was #7D00FF)
	secondaryColor = lipgloss.Color("#00E5FF") // Cyan / Electric Blue
	accentColor    = lipgloss.Color("#FF00FF") // Neon Magenta

	subtleColor  = lipgloss.Color("#666666")
	textColor    = lipgloss.Color("#EEEEEE")
	successColor = lipgloss.Color("#00FF99") // bright green
	errorColor   = lipgloss.Color("#FF3333") // bright red
	warningColor = lipgloss.Color("#FFD700") // gold

	// -- Layout Styles --

	// Main container
	docStyle = lipgloss.NewStyle().Padding(1, 2)

	// Panel Style (Subtle thin borders like Crush)
	panelStyle = lipgloss.NewStyle().
			Border(lipgloss.NormalBorder(), false, false, false, false). // No default borders
			Padding(0, 1)

	sidebarStyle = lipgloss.NewStyle().
			Border(lipgloss.NormalBorder(), false, false, false, true).
			BorderForeground(lipgloss.Color("#333333")).
			Padding(0, 2)

	separatorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#222222")).
			Margin(1, 0)

	// Textured background for headers
	headerBoxStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#000000")).
			Background(primaryColor).
			Bold(true).
			Padding(0, 1).
			MarginBottom(1)

	keywordStyle = lipgloss.NewStyle().
			Foreground(accentColor).
			Italic(true)

	asciiTexture = subtleStyle.Render(" //////////////////////////////////////////////////////// ")

	// -- Text Styles --

	titleStyle = lipgloss.NewStyle().
			Foreground(secondaryColor).
			Bold(true).
			Padding(0, 1).
			Background(lipgloss.Color("#333333"))

	headerStyle = lipgloss.NewStyle().
			Foreground(primaryColor).
			Bold(true)

	subtleStyle = lipgloss.NewStyle().
			Foreground(subtleColor)

	successStyle = lipgloss.NewStyle().
			Foreground(successColor).
			Bold(true)

	errorStyle = lipgloss.NewStyle().
			Foreground(errorColor).
			Bold(true)

	// -- Specific Component Styles --

	bannerTxt = `
                    $$\                         
                    \__|                        
 $$$$$$\   $$$$$$\  $$\  $$$$$$$\ $$$$$$\$$$$\  
$$  __$$\ $$  __$$\ $$ |$$  _____|$$  _$$  _$$\ 
$$ /  $$ |$$ |  \__|$$ | \$$$$$$\  $$ / $$ / $$ |
$$ |  $$ |$$ |      $$ |  \____$$\ $$ | $$ | $$ |
$$$$$$$  |$$ |      $$ | $$$$$$$  |$$ | $$ | $$ |
$$  ____/ \__|      \__| \_______/ \__| \__| \__|
$$ |                                            
$$ |                                            
\__|                                            `

	// Stats
	statLabelStyle = lipgloss.NewStyle().
			Foreground(subtleColor).
			Width(12)

	statValueStyle = lipgloss.NewStyle().
			Foreground(secondaryColor).
			Bold(true)

	// Inputs
	inputPromptStyle = lipgloss.NewStyle().
				Foreground(primaryColor).
				Bold(true).
				PaddingRight(1)

	// Search Results
	resultPathStyle = lipgloss.NewStyle().
			Foreground(textColor)

	resultScoreStyle = lipgloss.NewStyle().
				Foreground(subtleColor).
				Italic(true)

	selectedResultStyle = lipgloss.NewStyle().
				Border(lipgloss.NormalBorder(), false, false, false, true).
				BorderForeground(accentColor).
				Foreground(accentColor).
				PaddingLeft(1).
				Bold(true)

	// Menu Items
	selectedItemStyle = lipgloss.NewStyle().
				Foreground(secondaryColor).
				Bold(true)

	// Loading Screen
	loadingBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.DoubleBorder()).
			BorderForeground(primaryColor).
			Padding(1, 3).
			Align(lipgloss.Center)

	// Tiny Logs
	logTextStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#444444")).
			Italic(true).
			PaddingTop(1)

	// Tabs
	activeTabBorder = lipgloss.Border{
		Top:         "─",
		Bottom:      " ",
		Left:        "│",
		Right:       "│",
		TopLeft:     "╭",
		TopRight:    "╮",
		BottomLeft:  "┘",
		BottomRight: "└",
	}

	tabBorder = lipgloss.Border{
		Top:         "─",
		Bottom:      "─",
		Left:        "│",
		Right:       "│",
		TopLeft:     "╭",
		TopRight:    "╮",
		BottomLeft:  "┴",
		BottomRight: "┴",
	}

	tabStyle = lipgloss.NewStyle().
			Border(tabBorder, true).
			BorderForeground(subtleColor).
			Padding(0, 1)

	activeTabStyle = tabStyle.Copy().
			Border(activeTabBorder, true).
			BorderForeground(primaryColor).
			Foreground(primaryColor).
			Bold(true)

	tabGapStyle = tabStyle.Copy().
			BorderTop(false).
			BorderLeft(false).
			BorderRight(false).
			BorderBottom(true)
)

// RenderGradientBanner renders the banner with a diagonal gradient
func RenderGradientBanner() string {
	lines := strings.Split(bannerTxt, "\n")
	var out strings.Builder

	// Shimmering Palette
	c1, _ := colorful.Hex("#00E5FF") // Electric Blue
	c2, _ := colorful.Hex("#7D00FF") // Deep Indigo
	c3, _ := colorful.Hex("#FF00FF") // Neon Magenta

	for y, line := range lines {
		if strings.TrimSpace(line) == "" && y == 0 {
			continue
		}

		for x, char := range line {
			// Diagonal T (sum of X and Y normalized)
			// Adjust multipliers to stretch/shrink gradient
			normX := float64(x) / 40.0
			normY := float64(y) / float64(len(lines))
			t := (normX + normY) / 2.0

			var c colorful.Color
			if t < 0.5 {
				c = c1.BlendLuv(c2, t*2)
			} else {
				c = c2.BlendLuv(c3, (t-0.5)*2)
			}

			style := lipgloss.NewStyle().Foreground(lipgloss.Color(c.Hex())).Bold(true)
			out.WriteString(style.Render(string(char)))
		}
		out.WriteString("\n")
	}
	return out.String()
}
