import pandas as pd
import matplotlib.pyplot as plt
import mplcursors

# 1) Indlæs med korrekte headers fra linje 5 (header=4)
df = pd.read_excel('Kunder_Aktive_Brugere_1752151546.xlsx', header=4)

# 2) Fjern tomme kolonner
df = df.dropna(axis=1, how='all')

# 3) Identificér og vælg total-indtjeningen
rev_cols = [c for c in df.columns if 'indtjening' in c.lower()]
print("Fundne indtjening­-kolonner:", rev_cols)
rev_col = 'Indtjening' if 'Indtjening' in rev_cols else rev_cols[0]
print("Bruger kolonnen:", rev_col)

# Konverter den valgte indtjening-kolonne til numerisk (coerce tomme til NaN)
clean = (
    df[rev_col].astype(str)
               .str.replace(r'[^0-9,.-]', '', regex=True)
               .str.replace(',', '.', regex=False)
)
df[rev_col] = pd.to_numeric(clean, errors='coerce')

# Drop rækker uden Name eller værdi
df = df.dropna(subset=['Name', rev_col])

# 4) Print et udsnit
print("\n Alle nuværende kunder:")
print(df[['Name', rev_col, 'Kontrakttype']].head(10).to_string(index=False))

# 5) Top 25 efter samlet indtjening
top25 = df.nlargest(25, rev_col)
print("\n Top 25 kunder efter samlet indtjening:")
print(top25[['Name', rev_col, 'Kontrakttype']].to_string(index=False))

# 6) Bar-diagram med hover tooltips
fig, ax = plt.subplots()
bars = ax.bar(top25['Name'], top25[rev_col])
plt.setp(ax.get_xticklabels(), rotation=45, ha='right') 
ax.set_ylabel('Samlet indtjening (DKK)')
ax.set_title('Top 25 kunder – samlet indtjening')
fig.tight_layout()

cursor = mplcursors.cursor(bars, hover=True)
@cursor.connect("add")
def on_add(sel):
    idx = sel.index
    name = top25['Name'].iat[idx]
    val  = top25[rev_col].iat[idx]
    sel.annotation.set_text(f"{name}\n{val:,.0f} DKK")
    sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

plt.show()

# 7) Pie-chart → click to see customer names
fig2, ax2 = plt.subplots()

# Prepare data
df_clean = df.dropna(subset=['Kontrakttype'])
dist = df_clean['Kontrakttype'].value_counts()
grouped = df_clean.groupby('Kontrakttype')['Name'].apply(lambda x: '\n'.join(x.astype(str)))

# Draw pie chart
wedges, texts, autotexts = ax2.pie(
    dist,
    labels=dist.index,
    autopct='%1.1f%%',
    startangle=140,
    textprops={'fontsize': 9}
)
ax2.set_title('Fordeling af Kontrakttype', fontsize=14)

# Make wedges pickable
for w in wedges:
    w.set_picker(True)

# Define click handler
def on_pick(event):
    wedge = event.artist
    i = wedges.index(wedge)
    kt = dist.index[i]
    names = grouped.get(kt, "").split('\n')
    # Show only first 10 names + ellipsis
    preview = "\n".join(names[:10])
    if len(names) > 10:
        preview += "\n…"
    txt = f"{kt} ({len(names)} kunder):\n{preview}"
    
    # Remove previous annotations
    for child in ax2.get_children():
        if isinstance(child, plt.Annotation):
            child.remove()
    
    # Annotate at click position
    ax2.annotate(
        txt,
        xy=(event.mouseevent.xdata, event.mouseevent.ydata),
        xytext=(20,20),
        textcoords='offset points',
        bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.9),
        fontsize=8
    )
    fig2.canvas.draw()

# Connect the pick event
fig2.canvas.mpl_connect('pick_event', on_pick)

plt.tight_layout()
plt.show()

# 8) Growth of yearly subscription revenue by Start År
# Parse Start Dato as datetime and extract year
df['Start Dato'] = pd.to_datetime(df['Start Dato'], errors='coerce')
df = df.dropna(subset=['Start Dato'])
df['Start År'] = df['Start Dato'].dt.year.astype(int)

# Convert the subscription column
sub_col = 'Indtjening på abonnement (pr. år)'
df[sub_col] = (
    df[sub_col].astype(str)
               .str.replace(r'[^0-9,.-]', '', regex=True)
               .str.replace(',', '.', regex=False)
)
df[sub_col] = pd.to_numeric(df[sub_col], errors='coerce')
df = df.dropna(subset=[sub_col])

# Aggregate by year
yearly = df.groupby('Start År')[sub_col].sum().reset_index()

# Print table
print("\n🔹 Årlig abonnementsindtjening efter startår:")
print(yearly.to_string(index=False))

# Plot line chart
fig3, ax3 = plt.subplots()
ax3.plot(yearly['Start År'], yearly[sub_col], marker='o')
ax3.set_xlabel('Start År')
ax3.set_ylabel('Årlig abonnementsindtjening (DKK)')
ax3.set_title('Growth i abonnementsindtjening efter startår')
ax3.grid(True)
plt.tight_layout()
plt.show()

# 9) Fordeling gratis vs. betalte abonnements‐kunder
import matplotlib.pyplot as plt

sub_col = 'Indtjening på abonnement (pr. år)'

# Kategori‐opdeling
df['Abonnementstype'] = df[sub_col].fillna(0).apply(lambda x: 'Betalt' if x > 0 else 'Gratis')

# Tæl hvordan
dist2 = df['Abonnementstype'].value_counts()
# Saml navne pr. kategori
grouped2 = df.groupby('Abonnementstype')['Name'].apply(lambda x: '\n'.join(x))

# Tegn pie
fig4, ax4 = plt.subplots()
wedges2, texts2, autotexts2 = ax4.pie(
    dist2,
    labels=dist2.index,
    autopct='%1.1f%%',
    startangle=90,
    textprops={'fontsize': 11}
)
ax4.set_title('Gratis vs. Betalt abonnement', fontsize=14)

# Gør wedges klikbare
for w in wedges2:
    w.set_picker(True)

def on_pick2(event):
    wedge = event.artist
    idx = wedges2.index(wedge)
    kategori = dist2.index[idx]
    navne = grouped2[kategori].split('\n')
    preview = "\n".join(navne[:10])
    if len(navne) > 10:
        preview += "\n…"
    txt = f"{kategori} ({dist2[kategori]} kunder):\n\n{preview}"

    # Fjern gamle annotationer
    for child in ax4.get_children():
        if isinstance(child, plt.Annotation):
            child.remove()

    # Sæt ny annotation
    ax4.annotate(
        txt,
        xy=(event.mouseevent.xdata, event.mouseevent.ydata),
        xytext=(20, 20),
        textcoords='offset points',
        bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.9),
        fontsize=9
    )
    fig4.canvas.draw()

fig4.canvas.mpl_connect('pick_event', on_pick2)
plt.tight_layout()
plt.show()

# 10) Fordeling af Betalte Frakturer
import matplotlib.pyplot as plt
import mplcursors

# Kolonnenavne
total_col = rev_col                        # f.eks. "Indtjening"
fee_col   = 'indtjening gebyr/i alt'

# 10a) Konverter fee‐kolonnen til numerisk
df[fee_col] = (
    df[fee_col].astype(str)
               .str.replace(r'[^0-9,.-]', '', regex=True)
               .str.replace(',', '.', regex=False)
)
df[fee_col] = pd.to_numeric(df[fee_col], errors='coerce')

# 10b) Beregn Betalte Frakturer
df['Betalte Frakturer'] = df[total_col] - df[fee_col]

# 10c) Drop rækker uden værdi
df_frak = df.dropna(subset=['Betalte Frakturer'])

# 10d) Print top 10
top10_frak = df_frak.nlargest(10, 'Betalte Frakturer')
print("\n Top 10 kunder efter Betalte Frakturer:")
print(top10_frak[['Name', 'Betalte Frakturer']].to_string(index=False))

# 10e) Bar‐graf for top 10 med hover
fig5, ax5 = plt.subplots()
bars5 = ax5.bar(top10_frak['Name'], top10_frak['Betalte Frakturer'])
plt.setp(ax5.get_xticklabels(), rotation=45, ha='right')
ax5.set_ylabel('Betalte Frakturer (DKK)')
ax5.set_title('Top 10 kunder – Betalte Frakturer')
fig5.tight_layout()

cursor5 = mplcursors.cursor(bars5, hover=True)
@cursor5.connect("add")
def _(sel):
    idx = sel.index
    name = top10_frak['Name'].iat[idx]
    val  = top10_frak['Betalte Frakturer'].iat[idx]
    sel.annotation.set_text(f"{name}\n{val:,.0f} DKK")
    sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

plt.show()




