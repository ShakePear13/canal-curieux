package fr.canalcurieux.tv;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

/** Canal Curieux pour la TV : une simple fenêtre plein écran sur le site, pilotable à la télécommande. */
public class MainActivity extends Activity {
    private static final String SITE = "https://shakepear13.github.io/canal-curieux/";
    private static final int FOND = 0xFF141816;

    private FrameLayout racine;
    private WebView web;
    private View pleinEcran;
    private WebChromeClient.CustomViewCallback finPleinEcran;

    @Override
    protected void onCreate(Bundle etat) {
        super.onCreate(etat);
        racine = new FrameLayout(this);
        racine.setBackgroundColor(FOND);
        web = new WebView(this);
        web.setBackgroundColor(FOND);

        WebSettings r = web.getSettings();
        r.setJavaScriptEnabled(true);
        r.setDomStorageEnabled(true);          // vues, liste et réglages gardés sur la TV
        r.setDatabaseEnabled(true);
        r.setMediaPlaybackRequiresUserGesture(false);   // la vidéo démarre dès qu'on ouvre une fiche
        r.setUserAgentString(r.getUserAgentString() + " CanalCurieuxTV/1");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView vue, WebResourceRequest demande) {
                if (!demande.isForMainFrame()) return false;           // le lecteur intégré reste dans la page
                if (demande.getUrl().toString().startsWith(SITE)) return false;
                try {                                                   // tout autre lien s'ouvre dans l'appli adaptée
                    startActivity(new Intent(Intent.ACTION_VIEW, demande.getUrl()));
                } catch (Exception e) {
                    // aucune appli pour ce lien : on reste sur le site
                }
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onShowCustomView(View vue, CustomViewCallback rappel) {
                if (pleinEcran != null) {
                    rappel.onCustomViewHidden();
                    return;
                }
                pleinEcran = vue;
                finPleinEcran = rappel;
                racine.addView(vue, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
                web.setVisibility(View.GONE);
            }

            @Override
            public void onHideCustomView() {
                quitterPleinEcran();
            }
        });

        racine.addView(web, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(racine);
        if (etat == null) web.loadUrl(SITE); else web.restoreState(etat);
        web.requestFocus();
    }

    private void quitterPleinEcran() {
        if (pleinEcran == null) return;
        racine.removeView(pleinEcran);
        pleinEcran = null;
        web.setVisibility(View.VISIBLE);
        if (finPleinEcran != null) finPleinEcran.onCustomViewHidden();
        finPleinEcran = null;
        web.requestFocus();
    }

    @Override
    public void onBackPressed() {
        if (pleinEcran != null) quitterPleinEcran();
        else if (web.canGoBack()) web.goBack();      // ferme le lecteur avant de quitter l'appli
        else super.onBackPressed();
    }

    @Override
    protected void onSaveInstanceState(Bundle etat) {
        super.onSaveInstanceState(etat);
        web.saveState(etat);
    }

    @Override
    protected void onPause() {
        web.onPause();       // coupe la lecture quand on quitte l'appli
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }
}
