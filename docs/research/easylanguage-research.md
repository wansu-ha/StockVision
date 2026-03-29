# EasyLanguage (TradeStation) Comprehensive Feature Breakdown

**Research Date:** 2026-03-28
**Status:** Complete Reference Document
**Purpose:** Detailed feature-by-feature comparison for algorithmic trading language evaluation

---

## Table of Contents

1. [Data Types & Variables](#1-data-types--variables)
2. [Control Flow](#2-control-flow)
3. [Bar Reference Model](#3-bar-reference-model)
4. [Order Types](#4-order-types)
5. [Position Sizing](#5-position-sizing)
6. [Exit Types & Stop Management](#6-exit-types--stop-management)
7. [Multi-Data (Multiple Symbols/Timeframes)](#7-multi-data-multiple-symbolstimeframes)
8. [Input Parameters & Optimization](#8-input-parameters--optimization)
9. [Functions vs Indicators vs Strategies](#9-functions-vs-indicators-vs-strategies)
10. [State Management](#10-state-management)
11. [Event Model & Bar Processing](#11-event-model--bar-processing)
12. [Real-World Strategy Examples](#12-real-world-strategy-examples)

---

## 1. Data Types & Variables

### Primitive Data Types
EasyLanguage supports the following primitive types:
- **Numeric:** `float`, `double`, `int`
- **Boolean:** `bool` (true/false)
- **String:** `string`
- **Class Types:** User-defined classes

The language is **case-insensitive**.

### Pre-Declared Variables

EasyLanguage provides 100+ pre-initialized variables:
- **Numerical:** `Value0` through `Value99` (numeric variables)
- **Boolean:** `Condition0` through `Condition99` (true/false variables)

These can be used without explicit declaration.

### User-Declared Variables

**Syntax:**
```
Variable: myVar(0), anotherVar(1.5), flagVar(0);
Variable: myVar(initialValue), anotherVar(initialValue);
Var: myVar(0);  // shortened alias
Vars: var1(0), var2(0);
```

**Variable Naming Rules:**
- Up to 20 alphanumeric characters
- Can include `.` (period) and `_` (underscore)
- Cannot start with number or period
- Examples: `BuyLevel`, `stop_loss_amt`, `price.of.entry`

### Arrays

**Fixed Arrays:**
```
Arrays: prices[100], signals[50][10];  // up to 10 dimensions
```

**Dynamic Arrays:**
```
Arrays: dynamicArray[];  // single dimension only, no max size
dynamicArray.Add(value);
dynamicArray.RemoveAt(index);
```

**Array Indexing:**
- Arrays are **zero-indexed** (element 0 is first)
- **Important:** Most built-in functions ignore element 0, so best practice is not to use it
- Reference: `prices[5]`, `signals[3][2]`

---

## 2. Control Flow

### If...Then...Else Statement

**Basic Syntax:**
```
If condition Then
    statement1
Else
    statement2;
```

**Multi-line with Begin/End:**
```
If Close > Open Then Begin
    myVar = myVar + 1;
    buyFlag = True;
End
Else Begin
    myVar = 0;
    buyFlag = False;
End;
```

**Chained Conditions:**
```
If Close > SMA(Close, 50) Then
    myVar = 1
Else If Close > SMA(Close, 200) Then
    myVar = 2
Else
    myVar = 0;
```

### Switch/Case Statement

**Syntax:**
```
Switch (expression) Begin
    Case valueA:
        statement1;
    Case valueB:
        statement2;
    Default:
        statement3;
End;
```

**Use Case:** Useful for complex multi-branch conditions instead of nested if/else

### For Loop

**Standard For Loop:**
```
For counter = startValue To endValue Begin
    // loop body
End;

// Example: Calculate average of last 10 bars
sum = 0;
For i = 0 To 9 Begin
    sum = sum + Close[i];
End;
average = sum / 10;
```

### While Loop

**Syntax:**
```
While condition Begin
    // loop body
    // MUST eventually make condition False or infinite loop
End;

// Example: Find price level going back through bars
i = 0;
While i < 50 AND Close[i] > resistance Begin
    i = i + 1;
End;
```

**Important:** If condition is never true, loop never executes. Must contain logic to make condition false, or creates infinite loop (freezes platform).

### Repeat/Until Loop

**Syntax:**
```
Repeat Begin
    // loop body (executes at least once)
    // update condition variable
Until condition;

// Example
count = 0;
Repeat Begin
    count = count + 1;
    price = Close[count];
Until price < movingAvg OR count > 100;
```

**Key Difference:** Condition is tested **after** first execution (guaranteed at least one iteration).

### Loop Control

**Break Statement:**
```
For i = 0 To 100 Begin
    If Close[i] < SMA(Close, 20) Then
        Break;  // exits loop immediately
End;
// Control goes to next statement after End
```

---

## 3. Bar Reference Model

### The Bar Processing Model

EasyLanguage processes historical data bar-by-bar, **left to right** across the chart:

1. First bar is read as "current bar"
2. All EasyLanguage statements evaluate relative to current bar
3. Procedure runs, statements complete
4. Next bar is read from datafeed
5. Entire procedure runs again with new prices
6. **Result:** 500-bar chart = procedure runs 500 times total

### Price Data Access

**Current Bar Prices:**
```
Open  or O    // opening price of current bar
High  or H    // high price of current bar
Low   or L    // low price of current bar
Close or C    // closing price of current bar
```

### Historical Price References

**Bracket Notation (most common):**
```
Close[0]      // current bar (same as Close)
Close[1]      // previous bar (1 bar ago)
Close[3]      // 3 bars ago
High[1]       // high of previous bar
Low[5]        // low of 5 bars ago
```

**English Phrase Notation:**
```
Close of 1 bar ago      // equivalent to Close[1]
High of 3 bars ago      // equivalent to High[3]
Low of the last 5 bars  // NOT a valid syntax
```

### MaxBarsBack Setting

**Critical Setting:** `MaxBarsBack` specifies how many previous bars the strategy can reference:
- Prevents referencing bars that don't exist
- Default values vary by strategy/indicator
- Must be set appropriately in Strategy Properties
- If strategy needs `Close[100]`, set MaxBarsBack to at least 100

### Important Constraints

- Cannot reference **future bars** (no `Close[-1]` or `Close[next bar]`)
- Cannot "look ahead" to what hasn't happened yet
- Bar data is immutable after bar close (backtesting)

---

## 4. Order Types

EasyLanguage uses **4 fundamental order verbs** that work across all asset types (stocks, futures, options):

### Buy
```
Buy 100 shares;
Buy 10 contracts next bar at market;
Buy 1 contract next bar at Close[1] - 100 stop;
```

**Behavior:**
- Establishes or **adds to a long position**
- If short position exists, **covers entire short first**, then establishes long
- Example: Short 5, then Buy 3 → Covers all 5 short, goes Long 3

### Sell
```
Sell 100 shares next bar at market;
Sell entire position next bar at Open stop;
Sell 5 contracts at Close - 10 stop;
```

**Behavior:**
- **Liquidates a long position only**
- Can never establish a short position
- If long 5 and Sell 3 → Covers 3, leaves Long 2

### SellShort
```
SellShort 100 shares;
SellShort 5 contracts next bar at market;
SellShort 10 at Close + ATR(14) stop;
```

**Behavior:**
- Establishes or **adds to a short position**
- If long position exists, **liquidates entire long first**, then establishes short
- Example: Long 5, then SellShort 3 → Liquidates all 5 long, goes Short 3

### BuyToCover
```
BuyToCover 100 shares next bar at market;
BuyToCover entire position at High[1] + 2 * ATR(14) stop;
BuyToCover 5 at Close stop;
```

**Behavior:**
- **Covers a short position only**
- Can never establish a long position
- Closes short positions

### Legacy Keywords (Pre-TradeStation 6)

In older versions:
- `ExitLong` was equivalent to `Sell`
- `ExitShort` was equivalent to `BuyToCover`
- These are **deprecated** but may still appear in legacy code

### Order Placement Timing

**Standard Syntax:**
```
Buy 100 shares at market;                    // executes at next bar open
Buy 100 shares next bar at market;           // explicitly next bar open
Buy 100 shares at Close[1] stop;             // stop order at previous close
Buy 100 shares at Close + 10 limit;          // limit order
```

**Execution Options:**
- `at market` / no specification → market order at next bar open
- `next bar` → explicitly next bar open
- `stop` → stop-loss order triggered below/above price
- `limit` → limit order triggered at or better than price

---

## 5. Position Sizing

### Specifying Shares/Contracts

**Explicit Quantity:**
```
Buy 100 shares;          // 100 shares
Buy 5 contracts;         // 5 contracts
Sell 50 shares next bar at market;
SellShort 10 contracts;
```

**Default Position Size:**
If no quantity specified, TradeStation uses the default from **Strategy Properties → Trade size** setting.

### Position Sizing Methods

#### 1. Fixed Position Sizing
Same number of shares/contracts for each trade:
```
Buy 10 contracts;  // always 10 regardless of account equity
```

#### 2. Percent-Risk Position Sizing
Risk a fixed percentage of account equity (e.g., 2% risk per trade):

**Formula:**
```
Number of Contracts = Integer(
    AccountEquity × RiskPercent / TradingRisk
)
```

**Example:**
- Account: $100,000
- Risk per trade: 2% = $2,000
- Stop distance: $500 (ATR-based)
- Contracts = Integer(100,000 × 0.02 / 500) = Integer(4) = 4 contracts

#### 3. Portfolio Maestro Money Management
Built-in position sizing calculation:
```
Number of Contracts = Integer(
    Portfolio_Equity × psriskpercent / pstradingrisk
)
```
Where:
- `psriskpercent`: Percentage to risk (0.02 = 2%)
- `pstradingrisk`: Dollar amount at risk per trade

### PSCalc Function
```
Variable: myContractSize(0);
myContractSize = PSCalc(accountEquity, riskPercent, stopDistance);
```
Returns calculated shares/contracts based on account and risk parameters.

### Practical Examples

**Risk-Based Position Sizing Code:**
```
Variable: riskAmt(0), stopDistance(0), contracts(0);

// Calculate stop distance
stopDistance = Close - (Close - ATR(14) * 2);  // 2 ATR below entry

// Calculate contracts
riskAmt = AccountEquity * 0.02;  // risk 2% of equity
contracts = Integer(riskAmt / stopDistance);

// Buy with calculated position
Buy contracts contracts;
```

---

## 6. Exit Types & Stop Management

EasyLanguage provides **5 built-in exit functions** that can be used simultaneously:

### SetStopLoss

```
SetStopLoss(dollarAmount);
SetStopLoss(500);  // exit if down $500
```

**Behavior:**
- Sets fixed dollar risk from entry
- If entry at 100, risk $500 → exit triggered at 99.50
- Works in both long and short positions
- Liquidates entire position when triggered

### SetProfitTarget

```
SetProfitTarget(dollarAmount);
SetProfitTarget(1000);  // exit if up $1,000
```

**Behavior:**
- Sets fixed dollar profit target
- Entry at 100, target $1,000 → exit at 110
- Can be used alone or with stop loss
- Liquidates entire position when triggered

### SetBreakEven

```
SetBreakEven(profitToActivate);
SetBreakEven(200);  // move stop to breakeven after $200 profit
```

**Behavior:**
- Moves stop loss to entry price after minimum profit reached
- Entry at 100, needs $200 profit to activate → once up to 102, stop moves to 100
- Protects against loss while allowing profit runs
- Often combined with trailing stops

### SetDollarTrailing

```
SetDollarTrailing(trailingAmount);
SetDollarTrailing(300);  // trail stop $300 from peak profit
```

**Behavior:**
- Trails stop loss from **maximum profit** by fixed dollar amount
- Entry at 100, reaches 110 (peak) → stop at 109.70
- As price goes higher, stop follows
- Locks in profits while allowing upside

### SetPercentTrailing

```
SetPercentTrailing(percentOfPeak, activationProfit);
SetPercentTrailing(5, 1000);  // trail 5% from peak after $1,000 profit
```

**Behavior:**
- Trails stop by **percentage of peak profit** after minimum profit
- More responsive to volatility than dollar trailing
- Entry at 100, reaches 120 (peak), profit target 1000 → once up $1,000, trail 5% from peak

### Multiple Exits Simultaneously

```
SetStopLoss(500);           // hard stop at $500 loss
SetProfitTarget(2000);      // take profits at $2,000
SetDollarTrailing(300);     // also trail by $300 from peak
```

**Rules:**
- All non-zero stops are active simultaneously
- Whichever is triggered first closes position
- Each exit can be enabled/disabled independently
- Must use built-in functions (SetXXX), not manual orders, for proper position recognition

### Manual Stop/Limit Orders (Alternative)

For custom logic not covered by built-ins:
```
If MarketPosition = 1 Then  // if long
    Sell entire position next bar at Close[1] - 2*ATR(14) stop;

If MarketPosition = -1 Then  // if short
    BuyToCover entire position at Close[1] + 2*ATR(14) stop;
```

---

## 7. Multi-Data (Multiple Symbols/Timeframes)

### Accessing Secondary Data Streams

To reference a second symbol or different timeframe, use **data aliasing**:

**Syntax:**
```
Close data2      // close of second data stream
High data2       // high of second data stream
Open[3] data2    // open 3 bars ago of second data stream
ATR(14) data2    // ATR calculation on second data stream
```

**Current Bar References:**
```
Close data2              // same as Close[0] data2
High data2              // same as High[0] data2
Low[2] data2            // low 2 bars ago of data2
Close[5] data2 / High[5] data2  // ratio calculations
```

### Setting Up Multiple Data Streams

1. **Insert Second Symbol:**
   - Right-click chart → "Insert symbol"
   - Add symbol (can be different market or same market different timeframe)

2. **Edit Timeframe:**
   - Right-click chart → "Format symbol"
   - Select symbol to edit
   - Change timeframe (5-min, 15-min, 1-hour, daily, etc.)

3. **Data1 vs Data2 Hierarchy:**
   - **Data1:** Highest resolution, used for trade execution and entry signals
   - **Data2+:** Lower resolution, filters or confirmation signals

### Important Constraints

- **Data synchronization required:** All datastreams must have **same delay status**
  - Cannot mix live + delayed data (platform warning)
  - All must be live OR all must be delayed

- **Data1 dominance:** Entry/exit orders execute on Data1 bars
  - Data2 used for conditions/filters, not execution
  - Example: "Buy on Data1 close > Data2 moving average"

### Practical Multi-Timeframe Examples

**Daily Filter with Intraday Entry:**
```
// Data1 = 5-minute bars, Data2 = daily bars
If Close > Close[1] data2 Then  // today's close > yesterday's close
    If Close crosses above SMA(20) Then
        Buy 5 contracts;
```

**Multiple Symbol Confirmation:**
```
// Data1 = SPY, Data2 = QQQ
If Close > SMA(50) AND Close data2 > SMA(50) data2 Then
    Buy 10 shares;  // both strong
```

**Higher Timeframe Stop:**
```
// Data1 = 15-min, Data2 = 1-hour
stop_level = Low[1] data2 - ATR(14) data2;
If MarketPosition = 1 Then
    Sell entire position at stop_level stop;
```

---

## 8. Input Parameters & Optimization

### Input Syntax

**Declaration:**
```
Input: Period(20);                    // input named "Period" with default 20
Input: FastMA(10), SlowMA(50);       // multiple inputs
Input: RiskPercent(0.02);            // decimal input
Input: UseFilter(1);                 // 1 = true, 0 = false
```

**Usage in Code:**
```
Value1 = SMA(Close, Period);         // Period is parameterized

If Close > Value1 Then
    Buy Period shares;               // can use input in calculations
```

### Strategy Properties Dialog

Once inputs are declared, TradeStation automatically creates UI controls:
- **Edit Inputs:** Dialog with input fields
- **Charts:** Apply same strategy multiple times with different inputs
- **Backtesting:** Test individual parameter values

### Optimization

The **Optimizer** tests multiple parameter combinations:

**Optimization Range:**
```
// Optimizer will test Period = 10, 15, 20, 25, 30
Input: Period(20);  // default
// Then in Strategy Properties → Optimizer:
// Set optimization range: 10 to 30, step 5
```

**Optimization API (Advanced):**
```
// Uses TradeStation's EasyLanguage Optimization API classes
// Define security, strategy, and parameters to optimize
// Runs thousands of parameter combinations
// Returns results sorted by user-defined fitness metric
```

**Optimization Approaches:**

1. **Range Optimization:**
   - Test: Period from 10 to 50 in steps of 5
   - Creates: 9 test cases

2. **List Optimization:**
   - Test: Period = 5, 10, 20, 50, 100
   - Optimizer then tests other parameters with each Period

3. **Security/Interval Optimization:**
   - Test strategy across: multiple symbols, multiple timeframes
   - Finds which symbol/timeframe combo is most profitable

### Practical Input Examples

**Complete Strategy with Optimization:**
```
Input: FastMA(10), SlowMA(50), RiskPercent(0.02);

Variable: fast(0), slow(0);

fast = Average(Close, FastMA);
slow = Average(Close, SlowMA);

If fast crosses above slow Then
    Buy integer(AccountEquity * RiskPercent / 100) contracts;

If fast crosses below slow Then
    Sell entire position next bar at market;
```

---

## 9. Functions vs Indicators vs Strategies

### Functions

**Purpose:** Reusable calculation modules

**Characteristics:**
- Encapsulate calculations (not plotting)
- Can be called from indicators, strategies, or other functions
- Verified separately from calling code
- Returns single or array value
- Improves code reusability

**Structure:**
```
Function: MyAverage(price, length)
Begin
    MyAverage = Average(price, length);
End;

// Usage in indicator or strategy:
Value1 = MyAverage(Close, 20);
Value2 = MyAverage(High, 50);
```

**Key Advantage:** Write calculation once, use in multiple strategies

### Indicators

**Purpose:** Analysis/visualization on charts

**Characteristics:**
- Display calculations visually (plots, colors, text)
- Cannot execute orders (read-only)
- Run on all bars of chart (not just entry bar)
- Focus on presentation, not trading logic
- Typically plot functions' results

**Structure:**
```
Indicator: MyMovingAverage
Inputs: Length(20);
Variables: MA(0);

MA = Average(Close, Length);
Plot1(MA, "MA");  // display on chart
```

**Key Constraint:** Indicators don't trade, they only display

### Strategies

**Purpose:** Trading rules with entries/exits

**Characteristics:**
- Execute Buy/Sell/SellShort/BuyToCover orders
- Have fixed `MaxBarsBack` setting
- Backtested and automated
- Can access account/position info (MarketPosition, EntryPrice)
- Can use SetStopLoss, SetProfitTarget, etc.
- Focus on trading logic, not visualization

**Structure:**
```
Strategy: MyTrendFollower
Inputs: FastMA(10), SlowMA(50);
Variables: fast(0), slow(0), MP(0);

fast = Average(Close, FastMA);
slow = Average(Close, SlowMA);
MP = MarketPosition;

If fast crosses above slow AND MP = 0 Then
    Buy 10 contracts;

If fast crosses below slow AND MP <> 0 Then
    Sell entire position next bar at market;
```

**Key Feature:** Integration with TradeStation's backtester and live trader

### Relationship

```
Function
  ↓
  └─→ Called by Indicator (displays result)
  └─→ Called by Strategy (uses for entry/exit logic)
```

**Best Practice:**
- Put pure calculations in Functions
- Put plotting logic in Indicators
- Put trading rules in Strategies
- Call Functions from both Indicator and Strategy to avoid code duplication

---

## 10. State Management

### MarketPosition Variable

**Current Position Status:**
```
MarketPosition = 0   // flat (no position)
MarketPosition = 1   // long
MarketPosition = -1  // short
```

**Usage:**
```
If MarketPosition = 0 Then
    // can enter new position
    Buy 10 contracts;

If MarketPosition = 1 Then
    // currently long
    If Close < SMA(20) Then
        Sell entire position;

If MarketPosition = -1 Then
    // currently short
    If Close > SMA(20) Then
        BuyToCover entire position;
```

### Critical Issue: One-Bar Delay

**Problem:**
TradeStation updates MarketPosition at end of bar, but entry executes at bar close. When you check `MarketPosition` in the same bar you entered, it still shows previous state (not updated until next bar).

**Example:**
```
Buy 10 contracts at market;  // executes at current bar close
If MarketPosition = 1 Then    // still false on same bar!
    SetStopLoss(500);         // may not execute as expected
// MarketPosition becomes 1 only on next bar
```

**Solution:**
Use `EntriesToday` to track entries in current bar:
```
Buy 10 contracts;
If EntriesToday > 0 Then  // correctly identifies entry in current bar
    SetStopLoss(500);     // works properly
```

Or set stops **outside** entry logic:
```
If Close > SMA(50) AND MarketPosition = 0 Then
    Buy 10 contracts;

If MarketPosition = 1 Then  // next bar after entry
    SetStopLoss(500);       // now sees position correctly
```

### EntryPrice

Returns the average price of all entries in current position:
```
If MarketPosition = 1 Then Begin
    stopLevel = EntryPrice - ATR(14);
    Sell entire position at stopLevel stop;
End;
```

**Important:** Same one-bar delay as MarketPosition (not available same bar as entry)

### BarsSinceEntry / BarsSinceExit

**BarsSinceEntry(occurrence):**
```
// Number of bars since most recent entry (1-based)
If BarsSinceEntry(1) > 20 Then
    Sell entire position;  // exit if held > 20 bars
```

**BarsSinceExit(occurrence):**
```
// Number of bars since last closed position
If BarsSinceExit(1) > 5 Then  // at least 5 bars since last exit
    If Close crosses above SMA(20) Then
        Buy again;  // prevent re-entry too quickly
```

### Custom State Tracking

For complex logic, maintain explicit state variables:

```
Variable: inPosition(0), barsHeld(0), enteredBar(0);

// On entry bar
If Close > Open AND inPosition = 0 Then Begin
    Buy 10 contracts;
    inPosition = 1;
    enteredBar = CurrentBar;
End;

// Track holding period
If inPosition = 1 Then
    barsHeld = CurrentBar - enteredBar;

// Exit after time or condition
If inPosition = 1 AND barsHeld > 30 Then Begin
    Sell entire position;
    inPosition = 0;
    barsHeld = 0;
End;
```

### Persistent Variables (Serial Functions)

Variables maintain values across bar executions (unlike C/Java local variables):

```
Function: CountUp
Var: counter(0);  // persists across function calls

counter = counter + 1;  // increments each bar
CountUp = counter;      // return current value
```

Result: `counter` accumulates across bars (doesn't reset to 0 each bar)

---

## 11. Event Model & Bar Processing

### Bar Execution Model

**Default: OnBarClose**

Strategy evaluates all conditions at **close of each bar**:
```
For each historical bar (left to right):
  1. Read OHLC prices
  2. Evaluate all conditions
  3. Execute any orders
  4. Bar closes, move to next bar
```

Result: Entry/exit orders execute at next bar open (1-bar delay minimum)

### IntraBarOrderGeneration

**Attribute to Enable Intrabar Processing:**
```
Strategy IntraBarOrderGeneration = true
```

**Effect:**
- Strategy evaluates on **every tick/price change** within a bar
- Orders can execute multiple times **within the same bar**
- More realistic backtesting for intraday strategies

**Practical Impact:**
```
// Without IntraBarOrderGeneration:
If Close > 100 Then Buy next bar at market;
// Executes once per bar at close

// With IntraBarOrderGeneration = true:
If Close > 100 Then Buy next bar at market;
// Evaluates every tick, can execute intrabar
```

### Calculate Modes (NinjaTrader Equivalent)

Similar to NinjaTrader, control evaluation frequency:
```
Calculate = Calculate.OnBarClose       // once per bar
Calculate = Calculate.OnPriceChange    // every tick
Calculate = Calculate.OnEachTick       // every tick
```

### BarStatus for Intrabar Logic

When using intrabar processing, identify which part of bar:

```
If IntraBarOrderGeneration Then Begin
    If BarStatus = 0 Then  // first tick of bar
        // do once at bar open
    Else If BarStatus = 2 Then  // last tick of bar
        // do at bar close
End;
```

### Important Constraints

- **MaxBarsBack:** Strategy can reference historical bars (defined in properties)
- **No Future Knowledge:** Cannot reference Close[-1] or future prices
- **Orders Realistic:** Order timing matches actual execution mechanics
- **Slippage/Spread:** Backtester simulates fill prices, commissions

---

## 12. Real-World Strategy Examples

### Example 1: Simple Moving Average Crossover

**Concept:** Buy when fast MA crosses above slow MA, sell when it crosses below

**Complete Code:**
```
Strategy: MAcrossover
Inputs: FastLength(10), SlowLength(50), RiskPercent(0.02);

Variables:
    FastMA(0), SlowMA(0),
    riskAmt(0),
    stopDist(0),
    contracts(0),
    MP(0);

FastMA = Average(Close, FastLength);
SlowMA = Average(Close, SlowLength);

// Entry signals
If FastMA crosses above SlowMA AND MarketPosition = 0 Then Begin
    // Calculate position size
    stopDist = ATR(14) * 2;
    riskAmt = AccountEquity * RiskPercent;
    contracts = Integer(riskAmt / stopDist);

    // Buy with calculated size
    Buy contracts contracts next bar at market;

    // Set stops/targets
    SetStopLoss(stopDist * 100);     // $-based stop
    SetProfitTarget(stopDist * 200); // 2:1 reward
End;

// Exit signal
If FastMA crosses below SlowMA AND MarketPosition <> 0 Then
    Sell entire position next bar at market;
```

**Features Used:**
- Variables, inputs, control flow
- Order placement (Buy, Sell)
- Position sizing (risk-based)
- Built-in exits (SetStopLoss, SetProfitTarget)
- MarketPosition tracking
- Bar references (prices, moving averages)
- Optimization ready (FastLength, SlowLength, RiskPercent)

### Example 2: Breakout Strategy with ATR Stops

**Concept:** Buy breakout above 20-bar high with ATR-based trailing stop

**Complete Code:**
```
Strategy: BreakoutATRTrail
Inputs:
    LookbackBars(20),
    StopMultiplier(2.0),
    TrailAmount(1.5);

Variables:
    breakoutPrice(0),
    stopPrice(0),
    contracts(5),
    ATRval(0),
    FloorPrice(0),
    FloorHit(0);

// Calculate key levels
breakoutPrice = Highest(High, LookbackBars);
ATRval = AvgTrueRange(14);
stopPrice = breakoutPrice - (ATRval * StopMultiplier);

// Entry: price breaks above 20-bar high
If Close > breakoutPrice AND MarketPosition = 0 Then Begin
    Buy contracts contracts next bar at breakoutPrice stop;
    FloorPrice = EntryPrice - (ATRval * TrailAmount);
    FloorHit = 0;
End;

// Manage position if long
If MarketPosition = 1 Then Begin
    // Hard stop at initial level
    SetStopLoss(ATRval * StopMultiplier * 100);

    // Activate trailing stop after $500 profit
    If Close - EntryPrice > 500 Then
        SetDollarTrailing(ATRval * TrailAmount * 100);
End;

// Exit on bearish signal (fast exit)
If MarketPosition = 1 AND Close crosses below SMA(Close, 10) Then
    Sell entire position next bar at market;
```

**Features Used:**
- Multiple inputs for optimization
- Bar referencing (Highest, moving averages)
- Conditional entry logic
- Position sizing (fixed contracts)
- Multiple exit types (hard stop + trailing)
- State management (FloorPrice, FloorHit)
- Multi-condition entry/exit

### Example 3: Multi-Timeframe with Position Sizing

**Concept:** Daily trend filter + 15-min entries with volatility-adjusted sizing

**Setup:**
- Data1: 15-minute ES (E-mini S&P 500)
- Data2: Daily ES
- Filter: only trade if daily uptrend
- Entry: 15-min breakout
- Exit: daily trend breaks or time-based

**Complete Code:**
```
Strategy: MultiTimeframeVoladjust
Inputs:
    DailyPeriod(50),
    MinuteEntry(5),
    RiskPercent(0.025),
    MaxBarsInTrade(100);

Variables:
    DailyMA(0),
    MinuteHigh(0),
    ATRDaily(0),
    riskAmount(0),
    stopDist(0),
    contracts(0),
    barsInTrade(0),
    MP(0);

// Calculate on both timeframes
DailyMA = Average(Close data2, DailyPeriod);  // daily moving average
MinuteHigh = Highest(High, MinuteEntry);      // 15-min breakout level
ATRDaily = AvgTrueRange(14) data2;             // daily volatility

// Filter: only trade in daily uptrend
If Close data2 > DailyMA Then Begin
    // Entry: 15-min breakout in daily uptrend
    If Close crosses above MinuteHigh AND MarketPosition = 0 Then Begin
        // Position size based on daily ATR
        stopDist = ATRDaily * 2;
        riskAmount = AccountEquity * RiskPercent;
        contracts = Integer(riskAmount / stopDist);

        Buy contracts contracts next bar at market;
        SetStopLoss(stopDist * 100);
    End;
End;

// Track bars in position
If MarketPosition <> 0 Then
    barsInTrade = barsInTrade + 1
Else
    barsInTrade = 0;

// Exit conditions
If MarketPosition = 1 Then Begin
    // Exit if daily trend reverses
    If Close data2 < DailyMA Then
        Sell entire position next bar at market;

    // Exit if held > max bars
    If barsInTrade > MaxBarsInTrade Then
        Sell entire position next bar at market;

    // Time-of-day exit (exit 30 min before market close)
    If TimeToNextOpen < 30 Then  // last 30 min of day
        Sell entire position at market;
End;
```

**Features Used:**
- Multi-data streams (data2 for daily filter)
- Dynamic position sizing (risk-adjusted)
- Multiple timeframes synchronization
- Complex entry/exit logic
- State tracking (barsInTrade)
- Time-based logic (TimeToNextOpen)
- Inputs for optimization across parameters

### Example 4: Adaptive Risk Management

**Concept:** Position size adapts to market volatility; tighter stops in volatile markets

**Complete Code:**
```
Strategy: AdaptiveRiskMgmt
Inputs:
    BasePeriod(20),
    VolatilityThreshold(30),  // ATR value threshold
    MaxRisk(0.03),            // 3% max risk
    MinRisk(0.01);            // 1% min risk

Variables:
    FastMA(0),
    SlowMA(0),
    ATRval(0),
    adjustedRisk(0),
    stopDist(0),
    contractSize(0);

FastMA = Average(Close, BasePeriod);
SlowMA = Average(Close, BasePeriod * 2);
ATRval = AvgTrueRange(14);

// Adaptive risk: reduce in high volatility
If ATRval > VolatilityThreshold Then
    adjustedRisk = MinRisk  // tighter in volatile markets
Else
    adjustedRisk = MaxRisk; // normal risk in calm markets

// Entry
If FastMA crosses above SlowMA AND MarketPosition = 0 Then Begin
    stopDist = ATRval * 2;
    contractSize = Integer(
        AccountEquity * adjustedRisk / (stopDist * PointValue)
    );

    Buy contractSize contracts next bar at market;
    SetStopLoss(stopDist * 100);
    SetProfitTarget(stopDist * 200);
End;

// Exit on reversal
If FastMA < SlowMA AND MarketPosition <> 0 Then
    Sell entire position next bar at market;
```

**Features Used:**
- Conditional risk adjustment based on market state
- Adaptive position sizing
- Volatility measurement (ATR)
- Dynamic stop calculations
- Clean entry/exit logic

---

## Comparison: EasyLanguage vs StockVision Architecture

| Feature | EasyLanguage | StockVision Equivalent |
|---------|--------------|----------------------|
| **Data types** | float, int, bool, string, arrays | TypeScript types |
| **Control flow** | if/then/else, for, while, switch | JavaScript control flow |
| **Bar references** | Close[1], High[3] | Historical price arrays, lookback |
| **Order types** | Buy, Sell, SellShort, BuyToCover | Order execution API |
| **Position sizing** | Explicit contracts/shares | Dynamic position calculation |
| **Exit management** | SetStopLoss, SetProfitTarget, SetBreakEven, SetDollarTrailing, SetPercentTrailing | Custom exit logic + order management |
| **Multi-data** | Data2, Data3 (symbols/timeframes) | Multiple data sources, timeframe aggregation |
| **Input parameters** | Input: variable(default) | Settings/configuration |
| **Optimization** | Built-in optimizer over ranges | Backtest parameter testing |
| **State tracking** | MarketPosition, EntryPrice, BarsSinceEntry | Position manager, state store |
| **Bar model** | Processes left-to-right, one pass | Real-time events + historical replay |

---

## Key Takeaways for StockVision Design

### Strengths of EasyLanguage Design
1. **Explicit bar reference model** — Clear when you're looking back vs. current bar
2. **Built-in position tracking** — MarketPosition removes manual state management
3. **Integrated exit functions** — Can run multiple exits simultaneously
4. **Intrabar control** — Can toggle between bar-close and intrabar order generation
5. **Multi-data aliasing** — Clean syntax for multi-timeframe logic

### Challenges to Consider
1. **One-bar delay with MarketPosition** — Requires workarounds (EntriesToday, external tracking)
2. **No async/concurrent logic** — Linear bar-by-bar execution
3. **Limited data types** — No native complex objects (though classes added in recent versions)
4. **MaxBarsBack required** — Fixed lookback limit per strategy
5. **Optimization runs separately** — Not integrated into live trading

### StockVision Opportunities
- **Avoid one-bar delay:** Real-time state updates to position
- **Support intrabar logic natively:** Event-driven instead of bar-by-bar
- **Rich data types:** Full TypeScript type system
- **Flexible lookback:** Dynamic, unlimited historical data access
- **Live optimization:** Adapt parameters during live trading

---

## References

**Official TradeStation Documentation:**
- [Array (Reserved Word)](https://help.tradestation.com/10_00/eng/tsdevhelp/elword/word/array_reserved_word_.htm)
- [Variables](https://help.tradestation.com/10_00/eng/tsdevhelp/elword/el_definitions/variables.htm)
- [Else (Reserved Word)](https://help.tradestation.com/10_00/eng/tsdevhelp/elword/word/else_reserved_word_.htm)
- [IntraBarOrderGeneration (Reserved Word)](https://help.tradestation.com/10_00/eng/tsdevhelp/elword/word/intrabarordergeneration_reserved_word_.htm)
- [BuyToCover (Reserved Word)](https://help.tradestation.com/09_05/eng/tsdevhelp/Subsystems/elword/word/buytocover_reserved_word_.htm)
- [SetStopLoss (Reserved Word)](https://help.tradestation.com/09_01/tsdevhelp/subsystems/elword/word/setstoploss_reserved_word_.htm)
- [Strategy Built-In Stop Commands](https://help.tradestation.com/10_00/eng/TradeStationHelp/elanalysis/el_procedures/strategy_built-in_stop_commands.htm)
- [EasyLanguage Essentials](https://cdn.tradestation.com/uploads/EasyLanguage-Essentials.pdf)
- [Learning EasyLanguage Strategies](https://cdn.tradestation.com/uploads/Learning-EasyLanguage-Strategies.pdf)
- [EasyLanguage Optimization API Developer's Guide](https://help.tradestation.com/10_00/eng/tsdevhelp/elobject/resources/pdf/easylanguage_optimization_api.pdf)

**Community Resources:**
- [Precision Trading Systems - Code Examples](https://precisiontradingsystems.com/easy-language-code.htm)
- [George Pruitt - EasyLanguage Tutorials](https://georgepruitt.com/category/easylanguage/easylanguage-tutorial-easylanguage/)
- [EasyLanguage Mastery - Tutorials and Strategies](https://easylanguagemastery.com)
- [MarkPlex - Free EasyLanguage Tutorials](https://markplex.com/free-tutorials/)
- [Capstone Trading - EasyLanguage Examples](https://www.capstonetradingsystems.com/challenge-page/Easylanguage-examples-training)
- [QuantifiedStrategies - 100+ Backtested Strategies](https://www.quantifiedstrategies.com/tradestation-trading-strategies/)

**PDF Resources:**
- [EasyLanguage Cheat Sheet](https://georgepruitt.com/wp-content/uploads/2025/01/EZLang-CheatSheet.pdf)
- [EasyLanguage Extension SDK](https://cdn.tradestation.com/uploads/EasyLanguage-Extension-SDK.pdf)
- [EasyLanguage Reference Guide 2000i](http://unicorn.us.com/trading/ELreference2000i.pdf)

---

**Document Status:** Complete reference material for language feature evaluation
**Last Updated:** 2026-03-28
**Recommended Usage:** Comparison basis for StockVision strategy language design
