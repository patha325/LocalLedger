from pathlib import Path
import csv,io,json
import pandas as pd
import plotly.express as px
import streamlit as st
from finance import Ledger,CATEGORIES,money
import ai

st.set_page_config(page_title='LocalLedger',page_icon='◉',layout='wide')
st.markdown('''<style>.stApp{background:#f5f7fb}h1,h2,h3{color:#162b4d}div[data-testid="stMetric"]{background:white;padding:20px;border-radius:14px;border:1px solid #e5eaf2}</style>''',unsafe_allow_html=True)
DATA=Path(__file__).parent/'data';DATA.mkdir(exist_ok=True);(DATA/'documents').mkdir(exist_ok=True)
ledger=Ledger(DATA/'ledger.sqlite3')
st.title('LocalLedger')
st.caption('Your household, in one view · Local records · Verified totals')
accounts=ledger.accounts()
with st.sidebar:
    st.header('View')
    currency=st.selectbox('Currency',['SEK','EUR','GBP','USD'])
    owners=sorted({a['owner'] for a in accounts})
    selected=st.multiselect('People',owners,default=owners)
    model=st.text_input('Local Ollama model','qwen3:8b')
    st.caption('Currencies are reported separately. Internal household transfers remain excluded in person views.')
    if st.button('Load demonstration household',disabled=bool(accounts)):
        for name,owner in [('Current account','Alex'),('Savings','Alex'),('Partner account','Sam')]:ledger.add_account(name,owner,'SEK')
        for a in sorted(ledger.accounts(), key=lambda a: a["id"]):
            p=Path(__file__).parent/'examples'/f"{a['id']}.csv"
            ledger.import_csv(p.read_text(),a['id'],'date','description','amount')
        ledger.link(3,6);ledger.link(4,9)
        for r in ledger.rows():
            if r['description']=='Salary':ledger.categorise(r['id'],'Salary')
            if 'Groceries' in r['description']:ledger.categorise(r['id'],'Groceries')
        st.rerun()

tabs=st.tabs(['Overview','Accounts & import','Transactions','Transfers','Ask & documents'])
with tabs[0]:
    summary=ledger.summary(currency,selected)
    months=summary['months']
    month=st.selectbox('Month',['All months']+[r['month'] for r in months])
    shown=months if month=='All months' else [r for r in months if r['month']==month]
    cols=st.columns(3)
    for col,label,key in zip(cols,['Income','Expenses','Net cash flow'],['income','expenses','net']):col.metric(label,f"{sum(r[key] for r in shown)/100:,.2f} {currency}")
    st.caption('Based on imported records. Net cash flow is income minus expenses; it is not account balance or net worth. Confirmed internal transfers are excluded.')
    if months:
        df=pd.DataFrame(months);df[['income','expenses','net']]=df[['income','expenses','net']]/100
        st.plotly_chart(px.bar(df,x='month',y=['income','expenses'],barmode='group',color_discrete_sequence=['#18a999','#596cdd']),use_container_width=True)
        rows=[r for r in ledger.rows() if r['currency']==currency and r['owner'] in selected and not r['transfer'] and (month=='All months' or r['day'].startswith(month)) and (r['amount']<0 or r['category']=='Refund')]
        cats={}
        for r in rows:cats[r['category']]=cats.get(r['category'],0)-r['amount']/100
        if cats:st.plotly_chart(px.bar(x=list(cats.values()),y=list(cats),orientation='h',labels={'x':f'Net expenses ({currency})','y':'Category'}),use_container_width=True)
        st.download_button('Export summary',df.to_csv(index=False),'monthly-summary.csv','text/csv')
    else:st.info('Add accounts and import records, or load the demonstration household.')
with tabs[1]:
    with st.form('account'):
        st.subheader('Add an account')
        name=st.text_input('Account name');owner=st.text_input('Person / owner');cur=st.selectbox('Account currency',['SEK','EUR','GBP','USD']);opening=st.text_input('Opening balance before earliest imported transaction','0.00')
        if st.form_submit_button('Create account'):
            try:ledger.add_account(name,owner,cur,money(opening,'.'));st.rerun()
            except Exception as e:st.error(str(e))
    balances=ledger.balances()
    if balances:
        st.dataframe(pd.DataFrame([{**a,'opening':a['opening']/100,'balance':a['balance']/100} for a in balances]),hide_index=True)
        account=st.selectbox('Import into account',accounts,format_func=lambda a:f"{a['name']} · {a['owner']}")
        upload=st.file_uploader('Bank CSV',type=['csv'])
        delim=st.selectbox('CSV separator',[',',';','\t']);dec=st.selectbox('Decimal separator',['.',',']);fmt=st.selectbox('Date format',['%Y-%m-%d','%d/%m/%Y','%d.%m.%Y','%Y%m%d'])
        if upload:
            try:
                text=upload.getvalue().decode('utf-8-sig');reader=csv.DictReader(io.StringIO(text),delimiter=delim);fields=reader.fieldnames or []
                st.dataframe(pd.DataFrame(list(reader)).head(10),hide_index=True)
                dc=st.selectbox('Date column',fields);tc=st.selectbox('Description column',fields,index=min(1,len(fields)-1));ac=st.selectbox('Signed amount column',fields,index=min(2,len(fields)-1));ic=st.selectbox('Stable bank transaction ID (recommended)',['None']+fields)
                st.caption('Positive amounts are incoming; negative amounts are outgoing. Imports are atomic. Without bank IDs, exact repeated rows use occurrence-based deduplication; review overlapping exports.')
                if st.button('Import records'):
                    st.success(ledger.import_csv(text,account['id'],dc,tc,ac,fmt,dec,delim,None if ic=='None' else ic));st.rerun()
            except Exception as e:st.error(str(e))
with tabs[2]:
    rows=ledger.rows()
    if rows:
        st.dataframe(pd.DataFrame([{**r,'amount':r['amount']/100} for r in rows]),hide_index=True)
        r=st.selectbox('Transaction to categorise',rows,format_func=lambda r:f"#{r['id']} · {r['day']} · {r['description']} · {r['amount']/100:.2f} {r['currency']}")
        category=st.selectbox('Category',CATEGORIES,index=CATEGORIES.index(r['category']));remember=st.checkbox('Remember category for this exact merchant description')
        if st.button('Save category'):ledger.categorise(r['id'],category,remember);st.rerun()
        if st.button('Suggest with local LLM'):
            try:
                with st.spinner('Analysing locally…'):s=ai.suggest(r['description'],model)
                st.info(f'{s.category}: {s.reason}');st.caption('Select the suggestion above and save to apply it.')
            except Exception as e:st.error(f'Local model unavailable or invalid response: {e}')
with tabs[3]:
    st.subheader('Review internal transfers')
    st.write('Confirm movements between your included household accounts, including credit-card repayments. Matching amounts alone do not establish a transfer.')
    candidates=ledger.candidates()
    for a,b in candidates:
        with st.container(border=True):
            st.write(f"#{a['id']} {a['day']} {a['name']} → #{b['id']} {b['day']} {b['name']} · {b['amount']/100:.2f} {a['currency']}")
            st.caption(a['description']+' / '+b['description'])
            if st.button('Confirm transfer',key=f"pair{a['id']}-{b['id']}"):ledger.link(a['id'],b['id']);st.rerun()
    rows=ledger.rows()
    if rows:
        st.subheader('Match manually (including different booking months)')
        debits=[r for r in rows if r['amount']<0 and not r['transfer']];credits=[r for r in rows if r['amount']>0 and not r['transfer']]
        if debits and credits:
            label=lambda r:f"#{r['id']} {r['day']} {r['name']} {r['description']} {r['amount']/100:.2f} {r['currency']}"
            a=st.selectbox('Outgoing transaction',debits,format_func=label);b=st.selectbox('Incoming transaction',credits,format_func=label)
            if st.button('Link selected transactions'):
                try:ledger.link(a['id'],b['id']);st.rerun()
                except Exception as e:st.error(str(e))
    for tid in sorted({r['transfer'] for r in rows if r['transfer']}):
        st.write('Confirmed transfer',tid)
        if st.button('Undo',key=f'undo{tid}'):ledger.unlink(tid);st.rerun()
    st.caption('Unmatched movements remain in income/expenses until confirmed. Different currencies or transfer fees require separate review; automatic FX matching is not supported.')
with tabs[4]:
    q=st.text_input('Question about the selected household view','Explain the monthly income and expense trends.')
    if st.button('Explain verified summary'):
        try:
            context={'currency':currency,'people':selected,**ledger.summary(currency,selected)}
            with st.spinner('Analysing locally…'):answer=ai.explain(q,context,model)
            st.write(answer)
            with st.expander('Verified figures and source transaction IDs'):st.json(context)
        except Exception as e:st.error(f'Local model unavailable: {e}')
    st.subheader('Supporting documents · LibreIndex')
    st.caption('Documents provide cited context. They do not import ledger transactions or establish numerical totals. Upload text-based PDFs; scanned statements require OCR first.')
    doc=st.file_uploader('Receipt / statement / invoice',type=['pdf','txt','md'],key='doc')
    if doc and st.button('Save document'):
        (DATA/'documents'/Path(doc.name).name).write_bytes(doc.getvalue());st.success('Saved locally')
    embedding=st.text_input('Local embedding model','embeddinggemma')
    if st.button('Index supporting documents'):
        try:
            with st.spinner('Indexing locally…'):index=ai.documents(DATA/'documents',model,embedding).index()
            st.json(index.report.model_dump())
        except Exception as e:st.error(str(e))
    dq=st.text_input('Question about documents')
    if st.button('Ask documents'):
        try:
            with st.spinner('Searching locally…'):answer=ai.documents(DATA/'documents',model,embedding).ask(dq)
            st.write(answer.text)
            if answer.warning:st.warning(answer.warning)
            for citation in answer.citations:
                with st.expander(citation.location):st.write(citation.excerpt)
        except Exception as e:st.error(str(e))
